from spinn_utilities.overrides import overrides
# pacman imports
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, CPUCyclesPerTickResource
from pacman.model.resources import DTCMResource, SDRAMResource
from pacman.utilities import utility_calls

# spinn front end common imports
from spinn_front_end_common.utilities \
    import constants, exceptions, helpful_functions
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.interface.buffer_management.buffer_models\
    import AbstractReceiveBuffersToHost
from spinn_front_end_common.interface.buffer_management \
    import recording_utilities
from spinn_front_end_common.abstract_models.impl \
    import MachineDataSpecableVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType

# general imports
from enum import Enum
import struct


class ConwayBasicCell(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        AbstractReceiveBuffersToHost):
    """ Cell which represents a cell within the 2d fabric
    """

    PARTITION_ID = "STATE"

    TRANSMISSION_DATA_SIZE = 2 * 4  # has key and key
    STATE_DATA_SIZE = 1 * 4  # 1 or 2 based off dead or alive
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * 4  # alive states, dead states

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('STATE', 2),
               ('NEIGHBOUR_INITIAL_STATES', 3),
               ('RESULTS', 4)])

    def __init__(self, label, state):
        MachineVertex .__init__(self, label)

        config = globals_variables.get_simulator().config
        self._buffer_size_before_receive = None
        if config.getboolean("Buffers", "enable_buffered_recording"):
            self._buffer_size_before_receive = config.getint(
                "Buffers", "buffer_size_before_receive")
        self._time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self._receive_buffer_host = config.get(
            "Buffers", "receive_buffer_host")
        self._receive_buffer_port = helpful_functions.read_config_int(
            config, "Buffers", "receive_buffer_port")

        # app specific data items
        self._state = state

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "conways_cell.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT + 8

        # reserve memory regions
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value,
            size=setup_size, label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_SIZE, label="inputs")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.STATE.value,
            size=self.STATE_DATA_SIZE, label="state")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value,
            size=8, label="neighour_states")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RESULTS.value,
            size=recording_utilities.get_recording_header_size(1))

        # simulation.c requirements
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # get recorded buffered regions sorted
        spec.switch_write_focus(self.DATA_REGIONS.RESULTS.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP],
            self._time_between_requests, self._buffer_size_before_receive,
            iptags))

        # check got right number of keys and edges going into me
        partitions = \
            machine_graph.get_outgoing_edge_partitions_starting_at_vertex(self)
        if not utility_calls.is_single(partitions):
            raise exceptions.ConfigurationException(
                "Can only handle one type of partition. ")

        # check for duplicates
        edges = list(machine_graph.get_edges_ending_at_vertex(self))
        if len(set(edges)) != 8:
            output = ""
            for edge in edges:
                output += edge.pre_vertex.label + " : "
            raise exceptions.ConfigurationException(
                "I've got duplicate edges. This is a error. The edges are "
                "connected to these vertices \n {}".format(output))

        if len(edges) != 8:
            raise exceptions.ConfigurationException(
                "I've not got the right number of connections. I have {} "
                "instead of 9".format(
                    len(machine_graph.incoming_subedges_from_vertex(self))))

        for edge in edges:
            if edge.pre_vertex == self:
                raise exceptions.ConfigurationException(
                    "I'm connected to myself, this is deemed an error"
                    " please fix.")

        # write key needed to transmit with
        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)

        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        if key is None:
            spec.write_value(0)
            spec.write_value(0)
        else:
            spec.write_value(1)
            spec.write_value(key)

        # write state value
        spec.switch_write_focus(
            region=self.DATA_REGIONS.STATE.value)

        if self._state:
            spec.write_value(1)
        else:
            spec.write_value(0)

        # write neighbours data state
        spec.switch_write_focus(
            region=self.DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value)
        alive = 0
        dead = 0
        for edge in edges:
            state = edge.pre_vertex.state
            if state:
                alive += 1
            else:
                dead += 1

        spec.write_value(alive)
        spec.write_value(dead)

        # End-of-Spec:
        spec.end_specification()

    def get_data(self, buffer_manager, placement):
        data = list()

        # for buffering output info is taken form the buffer manager
        reader, data_missing = buffer_manager.get_data_for_vertex(placement, 0)

        # do check for missing data
        if data_missing:
            print "missing_data from ({}, {}, {}); ".format(
                placement.x, placement.y, placement.p)

        # get raw data
        raw_data = reader.read_all()

        elements = struct.unpack(
            "<{}I".format(len(raw_data) / 4), str(raw_data))
        for element in elements:
            if element == 0:
                data.append(False)
            else:
                data.append(True)

        # return the data
        return data

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(
            sdram=SDRAMResource(
                self._calculate_sdram_requirement()),
            dtcm=DTCMResource(0),
            cpu_cycles=CPUCyclesPerTickResource(0))
        resources.extend(recording_utilities.get_recording_resources(
            [constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP],
            self._receive_buffer_host, self._receive_buffer_port))
        return resources

    @property
    def state(self):
        return self._state

    def _calculate_sdram_requirement(self):
        return (constants.SYSTEM_BYTES_REQUIREMENT +
                self.TRANSMISSION_DATA_SIZE + self.STATE_DATA_SIZE +
                self.NEIGHBOUR_INITIAL_STATES_SIZE +
                constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP)

    def __repr__(self):
        return self.label

    @overrides(AbstractReceiveBuffersToHost.get_minimum_buffer_sdram_usage)
    def get_minimum_buffer_sdram_usage(self):
        return 1024

    @overrides(AbstractReceiveBuffersToHost.get_n_timesteps_in_buffer_space)
    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        return recording_utilities.get_n_timesteps_in_buffer_space(
            buffer_space, [100])

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [0]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, txrx, placement):
        return helpful_functions.locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RESULTS.value, txrx)
