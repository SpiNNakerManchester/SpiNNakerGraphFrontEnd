# dsg imports
from data_specification.enums.data_type import DataType

# pacman imports
from pacman.model.decorators.overrides import overrides
from pacman.model.graphs.machine.impl.machine_vertex \
    import MachineVertex
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.sdram_resource import SDRAMResource
from pacman.executor.injection_decorator import inject_items

# graph front end imports
from spinn_front_end_common.interface.buffer_management import \
    recording_utilities
from spinn_front_end_common.abstract_models. \
    abstract_provides_n_keys_for_partition import \
    AbstractProvidesNKeysForPartition
from .shallow_water_edge import ShallowWaterEdge
from spinnaker_graph_front_end.utilities.conf import config

# FEC imports
from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.abstract_models \
    .abstract_binary_uses_simulation_run import AbstractBinaryUsesSimulationRun
from spinn_front_end_common.interface.buffer_management.buffer_models \
    .abstract_receive_buffers_to_host import AbstractReceiveBuffersToHost
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.abstract_models.impl.machine_data_specable_vertex \
    import MachineDataSpecableVertex
from spinn_front_end_common.abstract_models.abstract_has_associated_binary \
    import AbstractHasAssociatedBinary
from spinn_front_end_common.interface.provenance \
    .provides_provenance_data_from_machine_impl \
    import ProvidesProvenanceDataFromMachineImpl

# general imports
from enum import Enum
import logging
import struct
import random

logger = logging.getLogger(__name__)


class ShallowWaterVertex(
    MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
    AbstractReceiveBuffersToHost, AbstractBinaryUsesSimulationRun,
    AbstractProvidesNKeysForPartition,
    ProvidesProvenanceDataFromMachineImpl):
    """ A vertex partition for a heat demo; represents a heat element.
    """

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('TIMING_DATA', 2),
               ('NEIGHBOUR_KEYS', 3),
               ('INIT_STATE_VALUES', 4),
               ('FINAL_STATES', 5),
               ('PROVENANCE', 6)])

    DATA_TYPE_OF_FLOAT = DataType.FLOAT_32

    FLOAT_SIZE_IN_BYTES = DATA_TYPE_OF_FLOAT.size

    # 1 for has key, 1 for key for the 8 directions
    NEIGHBOUR_DATA_REGION_SIZE = 16 * 4

    # 2 , 1 for window offset, 1 for time between sends
    TIMING_DATA_REGION_SIZE = 2 * 4

    # 1 int for has key, 1 int for the key
    TRANSMISSION_DATA_REGION_SIZE = 2 * 4

    # each state variable needs 4 bytes for their float data item.
    INIT_STATE_REGION_SIZE = (
        (8 * 3 * FLOAT_SIZE_IN_BYTES) +  # neighbour states
        (3 * FLOAT_SIZE_IN_BYTES) +  # my states
        (11 * FLOAT_SIZE_IN_BYTES))  # constants

    # arbitrary size for recording data (used in auto pause and resume)
    FINAL_STATE_REGION_SIZE = 6000

    # each state variable needs 4 bytes for the their float data item.
    # u,v,p
    FINAL_STATE_REGION_SIZE_PER_TIMER_TICK = 3 * FLOAT_SIZE_IN_BYTES

    # bool flags
    TRUE = 1
    FALSE = 0

    # the order of which directions are written to sdram
    # ORDER_OF_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    ORDER_OF_DIRECTIONS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]

    # model specific stuff
    _model_based_max_atoms_per_core = 1
    _model_n_atoms = 1

    def __init__(
            self, label, u, v, p, tdt, dx,
            dy, fsdx, fsdy, alpha, constraints=None):

        # resources used by a shallow water element vertex
        sdram = SDRAMResource(
            self.NEIGHBOUR_DATA_REGION_SIZE + self.TIMING_DATA_REGION_SIZE +
            self.TRANSMISSION_DATA_REGION_SIZE + self.INIT_STATE_REGION_SIZE +
            self.FINAL_STATE_REGION_SIZE + self.get_provenance_data_size(0) +
            config.getint("Buffers", "minimum_buffer_sdram"))

        self._resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(34),  # not used currently due to note being a
            # application graph vertex
            sdram=sdram)

        # inheritance stuff
        MachineVertex.__init__(
            self, label=label, constraints=constraints)
        AbstractReceiveBuffersToHost.__init__(self)
        AbstractProvidesNKeysForPartition.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        AbstractBinaryUsesSimulationRun.__init__(self)
        ProvidesProvenanceDataFromMachineImpl.__init__(
            self, self.DATA_REGIONS.PROVENANCE.value, 0)

        # app specific data items
        self._u = u
        self._v = v
        self._p = p

        # constants to move down
        self._tdt = tdt
        self._dx = dx
        self._dy = dy
        self._fsdx = fsdx
        self._fsdy = fsdy
        self._alpha = alpha

        # buffered data items (used for buffered recording)
        self._buffer_size_before_receive = None
        if config.getboolean("Buffers", "enable_buffered_recording"):
            self._buffer_size_before_receive = config.getint(
                "Buffers", "buffer_size_before_receive")
        self._time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self._receive_buffer_host = config.get(
            "Buffers", "receive_buffer_host")

    @overrides(AbstractProvidesNKeysForPartition.get_n_keys_for_partition)
    def get_n_keys_for_partition(self, partition, graph_mapper):
        return 7  # one for p, v, u, cu, cv, z, h

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        return self._resources  # standard resources

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        """ returns the c code name for the shallow water vertex

        :return:
        """
        return "shallow_water.aplx"

    @inject_items({'tdma_agenda': "TDMAAgenda"})
    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification,
        additional_arguments={"tdma_agenda"})
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor,
            tdma_agenda):
        """

        :param placement: the placement object for the dsg
        :param machine_graph: the graph object for this dsg
        :param routing_info: the routing info object for this dsg
        :param iptags: the collection of iptags generated by the tag allocator
        :param reverse_iptags: the collection of reverse iptags generated by\
                the tag allocator
        :param machine_time_step: time between timer calls
        :param time_scale_factor: adjustment on top of machine time step.
        :param spec: the writer interface
        :param tdma_agenda: the timing schedule for the graph.
        """

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT

        spec.comment("\n*** Spec for shallow water vertex Instance ***\n\n")

        # ###################################################################
        # Reserve SDRAM space for memory areas:

        spec.comment("\nReserving memory space for spike data region:\n\n")

        # Create the data regions for the spike source array:
        self._reserve_memory_regions(spec, setup_size)

        # handle simulation.c items
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # get recorded buffered regions sorted
        spec.switch_write_focus(self.DATA_REGIONS.FINAL_STATES.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP],
            self._time_between_requests, self._buffer_size_before_receive,
            iptags))

        # application specific data items
        self._write_transmission_keys(spec, routing_info, machine_graph)
        self._write_key_data(spec, routing_info, machine_graph)
        self._write_timing_data(spec, tdma_agenda)
        self._write_state_data(spec, machine_graph)

        # End-of-Spec:
        spec.end_specification()

    def _write_timing_data(self, spec, tdma_agenda):
        """ writes the timing agenda requirements for the c code
        
        :param spec: the dsg writer
        :param tdma_agenda: the tdma agenda for the graph.
        :return: None
        """
        spec.switch_write_focus(region=self.DATA_REGIONS.TIMING_DATA.value)
        spec.comment("writing timing data for this shallow water element \n")
        spec.write_value(
            data=tdma_agenda[self]['time_offset'], data_type=DataType.UINT32)
        spec.write_value(
            data=tdma_agenda[self]['time_between_packets'],
            data_type=DataType.UINT32)

    def _write_state_data(self, spec, machine_graph):
        """ writes the init state for the c code to read

        :param spec: the DSG specification object
        :return: None
        """
        spec.switch_write_focus(
            region=self.DATA_REGIONS.INIT_STATE_VALUES.value)
        spec.comment(
            "writing initial states for this shallow water element \n")
        edges = machine_graph.get_edges_ending_at_vertex(self)

        # add basic data elements
        spec.write_value(data=self._u, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(data=self._v, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(data=self._p, data_type=self.DATA_TYPE_OF_FLOAT)

        edges = machine_graph.get_edges_ending_at_vertex(self)

        # for each direction, write the source vertex's u,v,p which allows
        # the first timer tick to just run as normal
        for position in range(0, len(self.ORDER_OF_DIRECTIONS)):
            found = False
            for edge in edges:
                if isinstance(edge, ShallowWaterEdge):
                    if edge.compass == self.ORDER_OF_DIRECTIONS[position]:
                        # U = 0, V = 1, P = 2, Z = 3, H = 4, CV = 5, CU = 6
                        spec.write_value(
                            edge.pre_vertex.u,
                            data_type=self.DATA_TYPE_OF_FLOAT)
                        spec.write_value(
                            edge.pre_vertex.v,
                            data_type=self.DATA_TYPE_OF_FLOAT)
                        spec.write_value(
                            edge.pre_vertex.p,
                            data_type=self.DATA_TYPE_OF_FLOAT)
                        found = True
            if not found:
                raise exceptions.ConfigurationException(
                    "need a {} direction edge".format(
                        self.ORDER_OF_DIRECTIONS[position]))

        # constant elements
        spec.write_value(self._dx, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._dy, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._fsdx, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._fsdy, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._alpha, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._tdt / 8.0, data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._tdt / self._dx,
                         data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value(self._tdt / self._dy,
                         data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value((self._tdt + self._tdt) / 8.0,
                         data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value((self._tdt + self._tdt) / self._dx,
                         data_type=self.DATA_TYPE_OF_FLOAT)
        spec.write_value((self._tdt + self._tdt) / self._dy,
                         data_type=self.DATA_TYPE_OF_FLOAT)

    def get_provenance_data_from_machine(self, transceiver, placement):
        provenance_data = self._read_provenance_data(transceiver, placement)
        return self._read_basic_provenance_items(provenance_data, placement)

    def _reserve_memory_regions(self, spec, system_size):
        """

        :param spec:
        :param system_size:
        :return:
        """
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value,
            size=system_size, label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_REGION_SIZE, label="output")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.NEIGHBOUR_KEYS.value,
            size=self.NEIGHBOUR_DATA_REGION_SIZE, label="inputs")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.INIT_STATE_VALUES.value,
            size=self.INIT_STATE_REGION_SIZE, label="init state values")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.FINAL_STATES.value,
            size=self.FINAL_STATE_REGION_SIZE, label="final state values")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TIMING_DATA.value,
            size=self.TIMING_DATA_REGION_SIZE, label="timing data values")
        self.reserve_provenance_data_region(spec)

    def _write_transmission_keys(self, spec, routing_info, graph):
        """

        :param spec:
        :param routing_info:
        :param graph:
        :return:
        """

        # Every edge should have the same key
        partitions = graph.get_outgoing_edge_partitions_starting_at_vertex(
            self)
        for partition in partitions:
            key = routing_info.get_first_key_from_partition(partition)
            spec.switch_write_focus(
                region=self.DATA_REGIONS.TRANSMISSIONS.value)

            # Write Key info for this core:
            if key is None:

                # if there's no key, then two false's will cover it.
                spec.write_value(data=self.FALSE)
                spec.write_value(data=0)

            else:

                # has a key, thus set has key to 1 and then add key
                spec.write_value(data=self.TRUE)
                spec.write_value(data=key)

    def _write_key_data(self, spec, routing_info, graph):
        """

        :param spec:
        :param routing_info:
        :param graph:
        :return:
        """
        spec.switch_write_focus(region=self.DATA_REGIONS.NEIGHBOUR_KEYS.value)

        # get incoming edges
        incoming_edges = \
            graph.get_edges_ending_at_vertex_with_partition_name(self, "DATA")

        # verify n edges
        if len(incoming_edges) > 8:
            print incoming_edges
            raise exceptions.ConfigurationException(
                "Should only have 8 edge")

        # for each edge, write the base key, so that the cores can figure
        # which bit of data its received
        for position in range(0, len(self.ORDER_OF_DIRECTIONS)):
            found_edge = None
            for edge in incoming_edges:
                if edge.compass == self.ORDER_OF_DIRECTIONS[position]:
                    found_edge = edge

            if found_edge is not None:
                key = routing_info.get_first_key_for_edge(found_edge)
                spec.write_value(data=key)
            else:
                logger.warning(
                    "Something is odd here. missing edge for direction {}"
                        .format(self.ORDER_OF_DIRECTIONS[position]))
                spec.write_value(data_type=DataType.INT32, data=-1)

    @property
    def p(self):
        return self._p

    @property
    def u(self):
        return self._u

    @property
    def v(self):
        return self._v

    @p.setter
    def p(self, new_value):
        self._p = new_value

    @u.setter
    def u(self, new_value):
        self._u = new_value

    @v.setter
    def v(self, new_value):
        self._v = new_value

    def get_recorded_region_ids(self):
        return [0]

    def get_minimum_buffer_sdram_usage(self):
        return self.FINAL_STATE_REGION_SIZE

    def get_recording_region_base_address(self, txrx, placement):
        return helpful_functions.locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.FINAL_STATES.value, txrx)

    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        return recording_utilities.get_n_timesteps_in_buffer_space(
            buffer_space, [self.FINAL_STATE_REGION_SIZE_PER_TIMER_TICK])

    def get_data(self, buffer_manager, placement):

        # for buffering output info is taken form the buffer manager
        reader, data_missing = buffer_manager.get_data_for_vertex(placement, 0)

        # do check for missing data
        if data_missing:
            print "missing_data from ({}, {}, {}); ".format(
                placement.x, placement.y, placement.p)

        # get raw data
        raw_data = reader.read_all()

        length_of_data = len(raw_data)
        print length_of_data
        length_of_data2 = len(str(raw_data))
        print length_of_data2
        data3 = str(raw_data)
        print data3
        format_string = "<{0}{1}{0}{1}{0}{1}{0}{1}{0}{1}{0}{1}{0}{1}" \
            .format(len(raw_data) / (7 * self.DATA_TYPE_OF_FLOAT.size),
                    self.DATA_TYPE_OF_FLOAT.struct_encoding)

        testbytes = [hex(val) for val in bytearray(raw_data)]
        print testbytes

        # convert to float
        elements = struct.unpack(format_string, bytes(raw_data))

        # convert into keyed data one for p, v, u, cu, cv, z, h
        data = dict()
        data['p'] = list()
        data['u'] = list()
        data['v'] = list()
        data['cu'] = list()
        data['cv'] = list()
        data['z'] = list()
        data['h'] = list()

        # store elements
        for position in range(0, len(raw_data) / (7 * 4)):
            data['p'].append(elements[0 + (position * 7)] /
                             self.DATA_TYPE_OF_FLOAT.scale)
            data['u'].append(elements[1 + (position * 7)] /
                             self.DATA_TYPE_OF_FLOAT.scale)
            data['v'].append(elements[2 + (position * 7)] /
                             self.DATA_TYPE_OF_FLOAT.scale)
            data['cu'].append(elements[3 + (position * 7)] /
                              self.DATA_TYPE_OF_FLOAT.scale)
            data['cv'].append(elements[4 + (position * 7)] /
                              self.DATA_TYPE_OF_FLOAT.scale)
            data['z'].append(elements[5 + (position * 7)] /
                             self.DATA_TYPE_OF_FLOAT.scale)
            data['h'].append(elements[6 + (position * 7)] /
                             self.DATA_TYPE_OF_FLOAT.scale)

        return data
