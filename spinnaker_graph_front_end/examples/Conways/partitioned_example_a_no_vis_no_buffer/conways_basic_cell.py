# pacman imports
from spinn_utilities.overrides import overrides

from pacman.executor.injection_decorator \
    import supports_injection, inject_items
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, CPUCyclesPerTickResource
from pacman.model.resources import DTCMResource, SDRAMResource
from pacman.utilities import utility_calls

# spinn front end common imports
from spinn_front_end_common.utilities \
    import constants, exceptions, helpful_functions
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.abstract_models.impl \
    import MachineDataSpecableVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType


# general imports
from enum import Enum
import struct


@supports_injection
class ConwayBasicCell(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):
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
        super(ConwayBasicCell, self).__init__(label)

        # app specific elements
        self._state = state

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "conways_cell.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @inject_items({"n_machine_time_steps": "TotalMachineTimeSteps"})
    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification,
        additional_arguments={"n_machine_time_steps"})
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor,
            n_machine_time_steps):

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT

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
            size=(n_machine_time_steps * 4) + 4, label="results")

        # simulation .c requirements
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

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
                output += edge.pre_subvertex.label + " : "
            raise exceptions.ConfigurationException(
                "I've got duplicate edges. This is a error. The edges are "
                "connected to these vertices \n {}".format(output))

        if len(edges) != 8:
            raise exceptions.ConfigurationException(
                "I've not got the right number of connections. I have {} "
                "instead of 9".format(
                    len(machine_graph.incoming_subedges_from_subvertex(self))))

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
        spec.write_value(int(self._state))

        # write neighbours data state
        spec.switch_write_focus(
            region=self.DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value)
        alive = 0
        dead = 0
        for edge in edges:
            if edge.pre_vertex.state:
                alive += 1
            else:
                dead += 1

        spec.write_value(alive)
        spec.write_value(dead)

        # End-of-Spec:
        spec.end_specification()

    def get_data(self, transceiver, placement, n_machine_time_steps):
        # Get the data region base address where results are stored for the
        # core
        record_region_base_address = \
            helpful_functions.locate_memory_region_for_placement(
                placement, self.DATA_REGIONS.RESULTS.value, transceiver)

        # find how many bytes are needed to be read
        number_of_bytes_to_read = str(transceiver.read_memory(
            placement.x, placement.y, record_region_base_address, 4))
        number_of_bytes_to_read = \
            struct.unpack("<I", number_of_bytes_to_read)[0]

        # read the bytes
        if number_of_bytes_to_read != n_machine_time_steps * 4:
            raise exceptions.ConfigurationException(
                "number of bytes seems wrong")
        raw_data = str(transceiver.read_memory(
            placement.x, placement.y, record_region_base_address + 4,
            number_of_bytes_to_read))

        # convert to bools and return
        return [bool(element) for element in struct.unpack(
            "<{}I".format(n_machine_time_steps), raw_data)]

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        return ResourceContainer(
            sdram=SDRAMResource(
                self._calculate_sdram_requirement()),
            dtcm=DTCMResource(0),
            cpu_cycles=CPUCyclesPerTickResource(0))

    @property
    def state(self):
        return self._state

    @inject_items({"n_machine_time_steps": "TotalMachineTimeSteps"})
    def _calculate_sdram_requirement(self, n_machine_time_steps):
        return (constants.SYSTEM_BYTES_REQUIREMENT +
                self.TRANSMISSION_DATA_SIZE + self.STATE_DATA_SIZE +
                self.NEIGHBOUR_INITIAL_STATES_SIZE +
                n_machine_time_steps + 4)

    def __repr__(self):
        return self.label
