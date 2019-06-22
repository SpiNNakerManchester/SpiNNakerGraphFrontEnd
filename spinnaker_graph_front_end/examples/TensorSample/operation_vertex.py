import logging
import struct
from enum import Enum
from data_specification.utility_calls import get_region_base_address_offset
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.utilities.constants import DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES
from spinn_front_end_common.abstract_models.impl import (MachineDataSpecableVertex)
from pacman.model.resources import (ResourceContainer, ConstantSDRAM)
from spinn_front_end_common.utilities.exceptions import ConfigurationException


logger = logging.getLogger(__name__)


class OperationVertex(MachineVertex, AbstractHasAssociatedBinary,
                      MachineDataSpecableVertex):

    _ONE_WORD = struct.Struct("<i")

    OPER_TYPE_DATA_SIZE = 4  # int number
    TRANSMISSION_DATA_SIZE = 2 * 4 # has key and key
    RECORDING_DATA_SIZE = 4 # int result

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('OPER_TYPE', 0),
               ('TRANSMISSIONS', 1),
               ('RECORDED_OPER_RESULT', 2)])

    PARTITION_ID = "OPERATION_PARTITION"

    def __init__(self, label, oper_type):
        MachineVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        MachineDataSpecableVertex.__init__(self)

        self._constant_data_size = 4
        self.placement = None
        self._label = label
        self._oper_type = oper_type
        print("\n {}_vertex __init__".format(self._label))


    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(sdram=ConstantSDRAM(
             self.OPER_TYPE_DATA_SIZE + self.TRANSMISSION_DATA_SIZE + self.RECORDING_DATA_SIZE +
             DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES ))

        return resources

    def _reserve_memory_regions(self, spec):
        print("\n oper_vertex _reserve_memory_regions")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.OPER_TYPE.value,
            size=self.OPER_TYPE_DATA_SIZE, label="oper_type_values")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_SIZE, label="keys")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RECORDED_OPER_RESULT.value,
            size=self.RECORDING_DATA_SIZE, label="recorded_operation_result")

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        print("\n oper_vertex generate_machine_data_specification")
        self.placement = placement

        self._reserve_memory_regions(spec)

        ## check for duplicates
        edges = list(machine_graph.get_edges_ending_at_vertex(self))
        print("edges : ", edges)
        if len(edges) != 2:
            raise ConfigurationException(
                "I've not got the right number of connections. I have {} "
                "instead of 2".format(
                    len(machine_graph.get_edges_ending_at_vertex(self))))
        print(len(machine_graph.get_edges_ending_at_vertex(self)))
        for edge in edges:
            if edge.pre_vertex == self:
                raise ConfigurationException(
                    "I'm connected to myself, this is deemed an error"
                    " please fix.")
        pre_vertices_first_keys=[]
        for edge in edges:
            pre_vertices_first_keys.append(routing_info.get_routing_info_for_edge(edge).first_key)

        # write oper type value
        spec.switch_write_focus(self.DATA_REGIONS.OPER_TYPE.value)
        print("\n write oper type value ", self._oper_type)
        spec.write_value(self._oper_type)

        # write key needed to transmit with
        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)
        print("\n key is ", key)
        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        spec.write_value(0 if key is None else 1)
        spec.write_value(0 if key is None else key)

        # End-of-Spec:
        spec.end_specification()

    def read(self, placement, txrx):
        """ Get the data written into sdram

        :param placement: the location of this vertex
        :param txrx: the buffer manager
        :return: string output
        """
        # Get the App Data for the core
        app_data_base_address = txrx.get_cpu_information_from_core(
            placement.x, placement.y, placement.p).user[0]
        print("app_data_base_address ", app_data_base_address)
        # Get the provenance region base address
        base_address_offset = get_region_base_address_offset(
            app_data_base_address, self.DATA_REGIONS.RECORDED_OPER_RESULT.value)
        address = self._ONE_WORD.unpack(txrx.read_memory(
            placement.x, placement.y, base_address_offset, self._ONE_WORD.size))[0]
        print("read address from recording:",address)
        data = self._ONE_WORD.unpack(txrx.read_memory(
            placement.x, placement.y, address, self._ONE_WORD.size))[0]

        print("read data :", data)

        return data

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "tensorFlow_operation.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.SYNC
