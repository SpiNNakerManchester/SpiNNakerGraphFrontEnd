# pacman imports
from pacman.model.decorators.overrides import overrides
from pacman.model.graphs.machine.impl.machine_vertex import MachineVertex
from pacman.model.resources.iptag_resource import IPtagResource
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.sdram_resource import SDRAMResource

# spinn front end commom imports
from spinn_front_end_common.abstract_models.impl.\
    machine_data_specable_vertex import MachineDataSpecableVertex
from spinn_front_end_common.interface.buffer_management.buffer_models.\
    receives_buffers_to_host_basic_impl import \
    ReceiveBuffersToHostBasicImpl
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.interface.simulation.impl.\
    uses_simulation_impl import UsesSimulationImpl

# gfe imports
from spinnaker_graph_front_end.utilities.conf import config

# general imports
from enum import Enum
import struct


class ConwayBasicCell(
        MachineVertex, MachineDataSpecableVertex,
        ReceiveBuffersToHostBasicImpl, UsesSimulationImpl):
    """
    cell which represents a cell within the 2 d fabric
    """

    TRANSMISSION_DATA_SIZE = 2 * 4  # has key and key
    STATE_DATA_SIZE = 1 * 4  # 1 or 2 based off dead or alive
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * 4  # alive states, dead states

    VIS_PORT_NUM = 17892  # port number use

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('STATE', 2),
               ('NEIGHBOUR_INITIAL_STATES', 3),
               ('RESULTS', 4),
               ('BUFFERED_STATE_REGION', 5)])

    def __init__(self, label, machine_time_step, time_scale_factor, state):

        # resources used by the system.
        resources = ResourceContainer(
            sdram=SDRAMResource(0), dtcm=DTCMResource(0),
            cpu_cycles=CPUCyclesPerTickResource(0))

        MachineVertex .__init__(self, resources, label)
        ReceiveBuffersToHostBasicImpl.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        UsesSimulationImpl.__init__(self)

        # simulation data items
        self._machine_time_step = machine_time_step
        self._time_scale_factor = time_scale_factor

        # storage objects
        self._no_machine_time_steps = None

        # app specific data items
        self._state = state

    @overrides(MachineDataSpecableVertex.get_binary_file_name)
    def get_binary_file_name(self):
        return "conways_cell.aplx"

    @property
    @overrides(MachineVertex.model_name)
    def model_name(self):
        return "ConwayBasicCell"

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags):

        # Setup words + 1 for flags + 1 for recording size
        setup_size = (constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 8) * 4

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
        self.reserve_buffer_regions(
            spec, self.DATA_REGIONS.BUFFERED_STATE_REGION.value,
            [self.DATA_REGIONS.RESULTS.value],
            [constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP])

        # simulation .c requriements
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        data = self.data_for_simulation_data(
            self._machine_time_step, self._time_scale_factor)
        spec.write_array(data)

        # get recorded buffered regions sorted
        buffer_size_before_receive = config.getint(
            "Buffers", "buffer_size_before_receive")
        time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self.write_recording_data(
            spec, iptags, [constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP],
            buffer_size_before_receive, time_between_requests)

        # check got right number of keys and edges going into me
        partitions = \
            machine_graph.get_outgoing_edge_partitions_starting_at_vertex(self)
        if len(partitions) != 1:
            raise exceptions.ConfigurationException(
                "Can only handle one type of partition. ")

        # check for duplicates
        edges = machine_graph.get_edges_ending_at_vertex(self)
        empty_list = set()
        for edge in edges:
            empty_list.add(edge.pre_vertex.label)
        if len(empty_list) != 8:
            output = ""
            for edge in edges:
                output += edge.pre_vertex.label + " : "
            raise exceptions.ConfigurationException(
                "I've got duplicate edges. This is a error. The edges are "
                "connected to these vertices \n {}".format(output))

        if len(machine_graph.get_edges_ending_at_vertex(self)) != 8:
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
        key = routing_info.get_first_key_from_partition(partitions[0])

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
        for edge in machine_graph.get_edges_ending_at_vertex(self):
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
        reader, data_missing = \
            buffer_manager.get_data_for_vertex(
                placement, self.DATA_REGIONS.RESULTS.value,
                self.DATA_REGIONS.BUFFERED_STATE_REGION.value)

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
        return ResourceContainer(
            sdram=SDRAMResource(
                self._calculate_sdram_requirement()),
            dtcm=DTCMResource(0),
            cpu_cycles=CPUCyclesPerTickResource(0),
            iptags=[IPtagResource(
                config.get("Recording", "live_spike_host"),
                self.VIS_PORT_NUM, strip_sdp=False)])

    @property
    def state(self):
        return self._state

    def _calculate_sdram_requirement(self):
        return (((constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 8) * 4) +
                self.TRANSMISSION_DATA_SIZE + self.STATE_DATA_SIZE +
                self.NEIGHBOUR_INITIAL_STATES_SIZE +
                constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP +
                ReceiveBuffersToHostBasicImpl.get_buffer_state_region_size(1))

    def __repr__(self):
        return self._label
