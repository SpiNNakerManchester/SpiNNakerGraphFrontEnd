import logging
import struct
from enum import Enum
from data_specification.utility_calls import get_region_base_address_offset
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models.impl import (MachineDataSpecableVertex)
from spinn_front_end_common.utilities.constants import DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES
from pacman.executor.injection_decorator import inject_items
from pacman.model.resources import (ResourceContainer, ConstantSDRAM)

logger = logging.getLogger(__name__)


class ConstScalarVertex(MachineVertex,
                        AbstractHasAssociatedBinary,
                        MachineDataSpecableVertex):
    _ONE_WORD = struct.Struct("<I")

    TRANSMISSION_DATA_SIZE = 2 * 4 # has key and key
    INPUT_DATA_SIZE = 4 # constant int number
    RECORDING_DATA_SIZE = 4

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('TRANSMISSIONS', 0),
               ('INPUT', 1),
               ('RECORDING_CONST_VALUES', 2)])

    PARTITION_ID = "OPERATION"

    def __init__(self, label, constValue):
        MachineVertex.__init__(self, )
        AbstractHasAssociatedBinary.__init__(self)
        MachineDataSpecableVertex.__init__(self)

        print("\n const_vertex init")

        self._constant_data_size = 4
        self.placement = None
        # app specific elements
        self._constValue = constValue
        self._label = label
        print("const_value in the instance :",self._constValue)

    def _reserve_memory_regions(self, spec):
        print("\n const_vertex _reserve_memory_regions")

        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_SIZE, label="keys")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.INPUT.value,
            size=self.INPUT_DATA_SIZE, label="input_const_values")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RECORDING_CONST_VALUES.value,
            size=self.RECORDING_DATA_SIZE, label="recorded_const")

    @inject_items({"data_n_time_steps": "DataNTimeSteps"})
    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification,
        additional_arguments={"data_n_time_steps"})
    def generate_machine_data_specification(self, spec, placement, machine_graph,
                                            routing_info, iptags, reverse_iptags,
                                            machine_time_step, time_scale_factor, data_n_time_steps):
        print("\n const_vertex generate_machine_data_specification")

        self.placement = placement
        # reserve memory region
        self._reserve_memory_regions(spec)

        # write key needed to transmit with
        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)
        print("\n key is ", key)
        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        spec.write_value(0 if key is None else 1)
        spec.write_value(0 if key is None else key)

        # write constant value
        spec.switch_write_focus(self.DATA_REGIONS.INPUT.value)
        print("\n write constant value ", self._constValue)
        spec.write_value(self._constValue)

        # End-of-Spec:
        spec.end_specification()

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        print("\n {} resources_required".format(self._label))

        fixed_sdram = (self.TRANSMISSION_DATA_SIZE + self.INPUT_DATA_SIZE + self.RECORDING_DATA_SIZE +
                       DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES)

        print("fixed_sdram : ",fixed_sdram)
        return ResourceContainer(sdram=ConstantSDRAM(fixed_sdram))

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
            app_data_base_address, self.DATA_REGIONS.RECORDING_CONST_VALUES.value)
        address = self._ONE_WORD.unpack(txrx.read_memory(
            placement.x, placement.y, base_address_offset, self._ONE_WORD.size))[0]
        print("read address from recording:", address)
        data = self._ONE_WORD.unpack(txrx.read_memory(
            placement.x, placement.y, address, self._ONE_WORD.size))[0]

        print("read data :", data)

        return data

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        print("\n const_vertex get_binary_file_name")

        return "const_scalar.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.SYNC
