import logging
import struct
from enum import Enum

from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from spinnaker_graph_front_end.examples.TensorSample.vertex import Vertex
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinn_front_end_common.abstract_models.impl import (MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement, read_config_int)
from pacman.model.resources import (
    CPUCyclesPerTickResource, DTCMResource, ResourceContainer, SDRAMResource)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)


logger = logging.getLogger(__name__)


class ConstVertex(MachineVertex,
                  AbstractHasAssociatedBinary,
                  MachineDataSpecableVertex,
                  AbstractReceiveBuffersToHost):

    TRANSMISSION_DATA_SIZE = 2 * 4
    INPUT_DATA_SIZE = 4
    RECORDING_DATA_SIZE = 4

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('TRANSMISSIONS', 0),
               ('INPUT', 1),
               ('RECORDING_CONST_VALUES', 2)])

    PARTITION_ID = "ADDITION_PARTITION"

    def __init__(self, label, constValue):
        MachineVertex.__init__(self, )
        AbstractHasAssociatedBinary.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        AbstractReceiveBuffersToHost.__init__(self)

        print("\n const_vertex init")

        config = globals_variables.get_simulator().config
        self._buffer_size_before_receive = None
        if config.getboolean("Buffers", "enable_buffered_recording"):
            self._buffer_size_before_receive = config.getint(
                "Buffers", "buffer_size_before_receive")
        self._time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self._receive_buffer_host = config.get(
            "Buffers", "receive_buffer_host")
        self._receive_buffer_port = read_config_int(
            config, "Buffers", "receive_buffer_port")
        self._constant_data_size = 4
        self.placement = None
        # app specific elements
        self._constValue = constValue

    def get_data(self, transceiver, placement, n_machine_time_steps):
        print("\n const_vertex get_data ")

        # Get the data region base address where results are stored for the
        # core
        record_region_base_address = locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RECORDING_CONST_VALUES.value, transceiver)

        # find how many bytes are needed to be read
        number_of_bytes_to_read = \
            struct.unpack("<I", transceiver.read_memory(
                placement.x, placement.y, record_region_base_address, 4))[0]

        # read the bytes
        if number_of_bytes_to_read != n_machine_time_steps * 4:
            raise ConfigurationException("number of bytes seems wrong")
        raw_data = transceiver.read_memory(
            placement.x, placement.y, record_region_base_address + 4,
            number_of_bytes_to_read)

        # elements expected to be integers
        return [element for element in struct.unpack(
            "<{}I".format(n_machine_time_steps), raw_data)]

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        print("\n const_vertex resources_required")

        resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100), sdram=SDRAMResource(100))

        resources.extend(recording_utilities.get_recording_resources(
            [self._constant_data_size],
            self._receive_buffer_host, self._receive_buffer_port))

        return resources

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        print("\n const_vertex get_binary_file_name")

        return "tensorFlow_const.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.SYNC

    def generate_machine_data_specification(self, spec, placement, machine_graph, routing_info, iptags, reverse_iptags,
                                            machine_time_step, time_scale_factor):
        print("\n const_vertex generate_machine_data_specification")

        self.placement = placement
        # reserve memory region
        self._reserve_memory_regions(spec)

        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)
        print("\n key is ", key)
        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        spec.write_value(0 if key is None else 1)
        spec.write_value(0 if key is None else key)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.INPUT.value)
        print("\n write constant value ", self._constValue)
        spec.write_value(int(self._constValue))

        # write data for constant
        spec.switch_write_focus(self.DATA_REGIONS.RECORDING_CONST_VALUES.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            4, self._time_between_requests, 4, iptags))

        # End-of-Spec:
        spec.end_specification()

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
            size=4, label="recording")

    def get_minimum_buffer_sdram_usage(self):
        return self._constant_data_size

    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        return recording_utilities.get_n_timesteps_in_buffer_space(
            buffer_space, 4)

    def get_recorded_region_ids(self):
        return [0]

    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RECORDING.value, txrx)
