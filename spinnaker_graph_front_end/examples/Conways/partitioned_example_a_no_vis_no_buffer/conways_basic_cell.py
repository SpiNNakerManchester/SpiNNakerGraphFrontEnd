# pacman imports
from pacman.model.partitioned_graph.partitioned_vertex import PartitionedVertex
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.sdram_resource import SDRAMResource

# spinn front end commom imports
from spinn_front_end_common.abstract_models.\
    abstract_partitioned_data_specable_vertex import \
    AbstractPartitionedDataSpecableVertex
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.utilities import helpful_functions

# dsg imports
from data_specification.data_specification_generator import \
    DataSpecificationGenerator

# general imports
from enum import Enum
import struct


class ConwayBasicCell(
        PartitionedVertex, AbstractPartitionedDataSpecableVertex):
    """
    cell which represents a cell within the 2 d fabric
    """

    TRANSMISSION_DATA_SIZE = 2 * 4 # has key and key
    STATE_DATA_SIZE = 1 * 4 # 1 or 2 based off dead or alive
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * 4 # alive states, dead states

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('STATE', 2),
               ('NEIGHBOUR_INITIAL_STATES', 3),
               ('RESULTS', 4)])

    def __init__(self, label, machine_time_step, time_scale_factor, state):

        # resources used by the system.
        resources = ResourceContainer(
            sdram=SDRAMResource(0), dtcm=DTCMResource(0),
            cpu=CPUCyclesPerTickResource(0))

        PartitionedVertex.__init__(self, resources, label)
        AbstractPartitionedDataSpecableVertex.__init__(
            self, machine_time_step=machine_time_step,
            timescale_factor=time_scale_factor)
        self._state = state

    def get_binary_file_name(self):
        return "conways_cell.aplx"

    def generate_data_spec(
            self, placement, sub_graph, routing_info,  hostname,
            report_folder, ip_tags, reverse_ip_tags,
            write_text_specs, application_run_time_folder):

        data_writer, report_writer = \
            self.get_data_spec_file_writers(
                placement.x, placement.y, placement.p, hostname, report_folder,
                write_text_specs, application_run_time_folder)

        spec = DataSpecificationGenerator(data_writer, report_writer)

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
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RESULTS.value,
            size=(self.no_machine_time_steps * 4) + 4, label="results")

        # simulation .c requriements
        self._write_basic_setup_info(spec, self.DATA_REGIONS.SYSTEM.value)

        # check got right number of keys and edges going into me
        partitions = sub_graph.outgoing_edges_partitions_from_vertex(self)
        if len(partitions) != 1:
            raise exceptions.ConfigurationException(
                "Can only handle one type of partition. ")

        # check for duplicates
        edges = sub_graph.incoming_subedges_from_subvertex(self)
        empty_list = set()
        for edge in edges:
            empty_list.add(edge.pre_subvertex.label)
        if len(empty_list) != 8:
            output = ""
            for edge in edges:
                output += edge.pre_subvertex.label + " : "
            raise exceptions.ConfigurationException(
                "I've got duplicate edges. This is a error. The edges are "
                "connected to these vertices \n {}".format(output))

        if len(sub_graph.incoming_subedges_from_subvertex(self)) != 8:
            raise exceptions.ConfigurationException(
                "I've not got the right number of connections. I have {} "
                "instead of 9".format(
                    len(sub_graph.incoming_subedges_from_subvertex(self))))

        for edge in edges:
            if edge.pre_subvertex == self:
                raise exceptions.ConfigurationException(
                    "I'm connected to myself, this is deemed an error"
                    " please fix.")

        # write key needed to transmit with
        keys_and_masks = routing_info. \
            get_keys_and_masks_from_partition(partitions["STATE"])
        key = keys_and_masks[0].key

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
        for edge in sub_graph.incoming_subedges_from_subvertex(self):
            state = edge.pre_subvertex.state
            if state:
                alive += 1
            else:
                dead += 1

        spec.write_value(alive)
        spec.write_value(dead)


        # End-of-Spec:
        spec.end_specification()
        data_writer.close()

        return data_writer.filename

    def get_data(self, transceiver, placement):
        data = list()

        # Get the data region base address where results are stored for the core
        record_region_base_address = \
            helpful_functions.locate_memory_region_for_placement(
                placement, self.DATA_REGIONS.RESULTS.value, transceiver)

        # find how many bytes are needed to be read
        number_of_bytes_to_read = str(transceiver.read_memory(
            placement.x, placement.y, record_region_base_address, 4))
        number_of_bytes_to_read = \
            struct.unpack("<I", number_of_bytes_to_read)[0]

        # read the bytes
        if number_of_bytes_to_read != (self.no_machine_time_steps * 4):
            raise exceptions.ConfigurationException(
                "number of bytes seems wrong")
        else:
            raw_data = str(transceiver.read_memory(
                placement.x, placement.y, record_region_base_address + 4,
                number_of_bytes_to_read))

        # convert to ints
        elements = struct.unpack(
            "<{}I".format(self.no_machine_time_steps), raw_data)
        for element in elements:
            if element == 0:
                data.append(False)
            else:
                data.append(True)

        # return the data
        return data

    @property
    def resources_required(self):
        return ResourceContainer(
            sdram=SDRAMResource(
                self._calculate_sdram_requirement()),
            dtcm=DTCMResource(0),
            cpu=CPUCyclesPerTickResource(0))

    @property
    def state(self):
        return self._state

    def _calculate_sdram_requirement(self):
        return (((constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 8) * 4) +
                self.TRANSMISSION_DATA_SIZE + self.STATE_DATA_SIZE +
                self.NEIGHBOUR_INITIAL_STATES_SIZE +
                (self.no_machine_time_steps * 1) + 4)

    def is_partitioned_data_specable(self):
        return True

    def __repr__(self):
        return self._label