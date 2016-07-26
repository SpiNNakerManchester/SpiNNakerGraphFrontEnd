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
from spinn_front_end_common.interface.buffer_management.buffer_models.\
    receives_buffers_to_host_basic_impl import \
    ReceiveBuffersToHostBasicImpl
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions

# dsg imports
from data_specification.data_specification_generator import \
    DataSpecificationGenerator

# gfe imports
from spinnaker_graph_front_end.utilities.conf import config

# general imports
from enum import Enum
import struct


class ConwayBasicCell(
        PartitionedVertex, AbstractPartitionedDataSpecableVertex,
        ReceiveBuffersToHostBasicImpl):
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
               ('RESULTS', 4),
               ('BUFFERED_STATE_REGION', 5)])

    def __init__(self, label, machine_time_step, time_scale_factor, state):

        # resources used by the system.
        resources = ResourceContainer(
            sdram=SDRAMResource(0), dtcm=DTCMResource(0),
            cpu=CPUCyclesPerTickResource(0))

        PartitionedVertex.__init__(self, resources, label)
        ReceiveBuffersToHostBasicImpl.__init__(self)
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
        self.reserve_buffer_regions(
            spec, self.DATA_REGIONS.BUFFERED_STATE_REGION.value,
            [self.DATA_REGIONS.RESULTS.value],
            [(self.no_machine_time_steps * 4) + 4])

        # simulation .c requriements
        self._write_basic_setup_info(spec, self.DATA_REGIONS.SYSTEM.value)

        # get recorded buffered regions sorted
        buffer_size_before_receive = config.getint(
            "Buffers", "buffer_size_before_receive")
        time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self.write_recording_data(
            spec, ip_tags, [(self.no_machine_time_steps * 4) + 4],
            buffer_size_before_receive, time_between_requests)

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

        # convert to ints
        elements = struct.unpack(
            "<{}I".format(self.no_machine_time_steps), str(raw_data))
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
                ReceiveBuffersToHostBasicImpl.get_buffer_state_region_size(1) +
                (self.no_machine_time_steps * 1) + 4)

    def is_partitioned_data_specable(self):
        return True

    def __repr__(self):
        return self._label