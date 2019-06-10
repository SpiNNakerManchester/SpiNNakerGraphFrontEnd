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


logger = logging.getLogger(__name__)


class AdditionVertex(MachineVertex, AbstractHasAssociatedBinary,
                     MachineDataSpecableVertex):
    _ONE_WORD = struct.Struct("<I")

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('RECORDED_ADDITION_RESULT', 1)])

    CORE_APP_IDENTIFIER = 0xBEEF

    def __init__(self, label, constraints=None):
        MachineVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        MachineDataSpecableVertex.__init__(self)

        print("\n add_vertex __init__")

        self._string_data_size = 5000
        self._constant_data_size = 4
        self.placement = None
        self._label = label

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(sdram=ConstantSDRAM(
            DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES + 4))

        return resources

    def _reserve_memory_regions(self, spec):
        print("\n add_vertex _reserve_memory_regions")

        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RECORDED_ADDITION_RESULT.value,
            size=4,
            label="recorded_addition_result")

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        print("\n add_vertex generate_machine_data_specification")
        self.placement = placement

        self._reserve_memory_regions(spec)

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
            app_data_base_address, self.DATA_REGIONS.RECORDED_ADDITION_RESULT.value)
        address = self._ONE_WORD.unpack(txrx.read_memory(
            placement.x, placement.y, base_address_offset, self._ONE_WORD.size))[0]
        data = self._ONE_WORD.unpack(txrx.read_memory(
            placement.x, placement.y, address, self._ONE_WORD.size))[0]

        print("read data :", data)

        return data

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "tensorFlow_addition.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.SYNC
