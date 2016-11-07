
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

# graph front end imports
from .weather_edge import WeatherDemoEdge
from spinnaker_graph_front_end.utilities.conf import config

# FEC imports
from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.abstract_models\
    .abstract_binary_uses_simulation_run import AbstractBinaryUsesSimulationRun
from spinn_front_end_common.interface.buffer_management.buffer_models.\
    receives_buffers_to_host_basic_impl import \
    ReceiveBuffersToHostBasicImpl
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.abstract_models.impl.machine_data_specable_vertex \
    import MachineDataSpecableVertex
from spinn_front_end_common.abstract_models.abstract_has_associated_binary \
    import AbstractHasAssociatedBinary

# general imports
from enum import Enum
import logging
import struct

logger = logging.getLogger(__name__)


class WeatherVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        ReceiveBuffersToHostBasicImpl, AbstractBinaryUsesSimulationRun):
    """ A vertex partition for a heat demo; represents a heat element.
    """

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('NEIGHBOUR_KEYS', 2),
               ('INIT_STATE_VALUES', 4),
               ('FINAL_STATES', 5)])

    # 3 int for EAST, NORTH_EAST, NORTH for u
    # 3 int for EAST, NORTH_EAST, NORTH for v
    # 3 int for EAST, NORTH_EAST, NORTH for p
    # 3 int for EAST, NORTH_EAST, NORTH for z
    # 3 int for EAST, NORTH_EAST, NORTH for h
    # 3 int for EAST, NORTH_EAST, NORTH for cv
    # 3 int for EAST, NORTH_EAST, NORTH for cu
    NEIGHBOUR_DATA_REGION_SIZE = 21 * 4
    
    # 1 int for has key, 1 int for the key
    TRANSMISSION_DATA_REGION_SIZE = 2 * 4
    
    # each state variable needs 4 bytes for their s15:16 data item.
    # u,v,p,psi,at_edge_east, hceu,dcep,hcev,at_edge_ne,at_edge_n, tdtd,
    # dx, dy, fsdx, fsdy, alpha
    INIT_STATE_REGION_SIZE = 22 * 8

    # each state variable needs 4 bytes for the their s15:16 data item.
    # u,v,p
    FINAL_STATE_REGION_SIZE = 3 * 4

    TRUE = 0
    FALSE = 1

    _model_based_max_atoms_per_core = 1
    _model_n_atoms = 1

    def __init__(
            self, label, u, v, p, psi, at_edge_east,
            hard_coded_east_u, hard_coded_east_p, hard_coded_east_v,
            at_edge_north_east, hard_coded_north_east_u,
            hard_coded_north_east_p, hard_coded_north_east_v,
            at_edge_north, hard_coded_north_u, hard_coded_north_p,
            hard_coded_north_v, tdt, dx, dy, fsdx, fsdy, alpha,
            constraints=None):

        # resources used by a weather element vertex
        sdram = SDRAMResource(
            23 + config.getint("Buffers", "minimum_buffer_sdram"))
        resources = ResourceContainer(cpu_cycles=CPUCyclesPerTickResource(45),
                                      dtcm=DTCMResource(34),
                                      sdram=sdram)
        MachineVertex.__init__(
            self, label=label, resources_required=resources,
            constraints=constraints)

        # app specific data items
        self._u = u
        self._v = v
        self._p = p
        self._psi = psi
        self._at_edge_east = at_edge_east
        self._at_edge_north_east = at_edge_north_east
        self._at_edge_north = at_edge_north

        # constants to move down
        self._tdt = tdt
        self._dx = dx
        self._dy = dy
        self._fsdx = fsdx
        self._fsdy = fsdy
        self._alpha = alpha

        # hard coded values
        self._hard_coded_east_u = hard_coded_east_u
        self._hard_coded_east_p = hard_coded_east_p
        self._hard_coded_east_v = hard_coded_east_v
        self._hard_coded_north_east_u = hard_coded_north_east_u
        self._hard_coded_north_east_p = hard_coded_north_east_p
        self._hard_coded_north_east_v = hard_coded_north_east_v
        self._hard_coded_north_u = hard_coded_north_u
        self._hard_coded_north_p = hard_coded_north_p
        self._hard_coded_north_v = hard_coded_north_v

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        """ returns the c code name for the weather vertex

        :return:
        """
        return "weather.aplx"

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):
        """

        :param placement: the placement object for the dsg
        :param machine_graph: the graph object for this dsg
        :param routing_info: the routing info object for this dsg
        :param iptags: the collection of iptags generated by the tag allocator
        :param reverse_iptags: the collection of reverse iptags generated by\
                the tag allocator
        :param spec: the writer interface
        """

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT

        spec.comment("\n*** Spec for Weather vertex Instance ***\n\n")

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

        # application specific data items
        self._write_transmission_keys(spec, routing_info, machine_graph)
        self._write_key_data(spec, routing_info, machine_graph)
        self._write_state_data(spec)

        # End-of-Spec:
        spec.end_specification()

    def _write_state_data(self, spec):
        """

        :param spec:
        :return:
        """
        spec.switch_write_focus(
            region=self.DATA_REGIONS.INIT_STATE_VALUES.value)
        spec.comment("writing initial states for this weather element \n")

        # add basic data elements
        spec.write_value(data=self._u, data_type=DataType.S3231)
        spec.write_value(data=self._v, data_type=DataType.S3231)
        spec.write_value(data=self._p, data_type=DataType.S3231)
        spec.write_value(data=self._psi, data_type=DataType.S3231)

        # if at a edge, add hard coded ones (to remove excess cores)
        if self._at_edge_east:
            spec.write_value(self.TRUE)
            spec.write_value(self._hard_coded_east_u, data_type=DataType.S3231)
            spec.write_value(self._hard_coded_east_v, data_type=DataType.S3231)
            spec.write_value(self._hard_coded_east_p, data_type=DataType.S3231)
        else:
            spec.write_value(self.FALSE)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
        if self._at_edge_north_east:
            spec.write_value(self.TRUE)
            spec.write_value(
                self._hard_coded_north_east_u, data_type=DataType.S3231)
            spec.write_value(
                self._hard_coded_north_east_v, data_type=DataType.S3231)
            spec.write_value(
                self._hard_coded_north_east_p, data_type=DataType.S3231)
        else:
            spec.write_value(self.FALSE)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
        if self._at_edge_north:
            spec.write_value(self.TRUE)
            spec.write_value(
                self._hard_coded_north_u, data_type=DataType.S3231)
            spec.write_value(
                self._hard_coded_north_v, data_type=DataType.S3231)
            spec.write_value(
                self._hard_coded_north_p, data_type=DataType.S3231)
        else:
            spec.write_value(self.FALSE)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
            spec.write_value(-1, data_type=DataType.INT32)
        spec.write_value(self._tdt, data_type=DataType.S3231)
        spec.write_value(self._dx, data_type=DataType.S3231)
        spec.write_value(self._dy, data_type = DataType.S3231)
        spec.write_value(self._fsdx, data_type = DataType.S3231)
        spec.write_value(self._fsdy, data_type = DataType.S3231)
        spec.write_value(self._alpha, data_type = DataType.S3231)

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
                spec.write_value(data=0)
                spec.write_value(data=0)

            else:

                # has a key, thus set has key to 1 and then add key
                spec.write_value(data=1)
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
        edge_partitions = ["DATA_S", "DATA_SW", "DATA_W"]
        for edge_partition in edge_partitions:
            incoming_edges = \
                graph.get_edges_ending_at_vertex_with_partition_name(
                    self, edge_partition)

            if len(incoming_edges) > 1:
                raise exceptions.ConfigurationException(
                    "Should only have 1 edge")

            if len(incoming_edges) == 1:
                incoming_edge = incoming_edges[0]
                key = routing_info.get_first_key_for_edge(incoming_edge)
                spec.write_value(data=key)
            else:
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

    def get_data(self, transceiver, placement):

        # Get the data region base address where results are stored for the
        # core
        record_region_base_address = \
            helpful_functions.locate_memory_region_for_placement(
                placement, self.DATA_REGIONS.FINAL_STATES.value, transceiver)

        # find how many bytes are needed to be read
        number_of_bytes_to_read = str(transceiver.read_memory(
            placement.x, placement.y, record_region_base_address, 4))

        number_of_bytes_to_read = \
            struct.unpack("<I", number_of_bytes_to_read)[0]

        # read the bytes
        if number_of_bytes_to_read != (self._n_machine_time_steps * 4):
            raise exceptions.ConfigurationException(
                "number of bytes seems wrong")
        else:
            raw_data = str(transceiver.read_memory(
                placement.x, placement.y, record_region_base_address + 4,
                number_of_bytes_to_read))

        # convert to float
        elements = struct.unpack(
            "<{}III".format(self._n_machine_time_steps), raw_data)

        # convert into keyed data
        data = dict()
        data['p'] = elements[0] / 32767.0
        data['u'] = elements[1] / 32767.0
        data['v'] = elements[2] / 32767.0

        return data
