import logging
from enum import Enum

from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType
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


class AdditionVertex(MachineVertex, AbstractHasAssociatedBinary,
                     MachineDataSpecableVertex,
                     AbstractReceiveBuffersToHost):

    INPUT_DATA_SIZE = 4
    RECORDING_DATA_SIZE = 4

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('INPUT_CONST_VALUES', 0),
               ('RECORDED_ADDITION_RESULT', 1)])

    CORE_APP_IDENTIFIER = 0xBEEF

    def __init__(self, label, constraints=None):
        MachineVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        AbstractReceiveBuffersToHost.__init__(self)

        print("\n add_vertex __init__")

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

        self._string_data_size = 5000
        self._constant_data_size = 4
        self.placement = None

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100), sdram=SDRAMResource(100))

        resources.extend(recording_utilities.get_recording_resources(
            [self._constant_data_size],
            self._receive_buffer_host, self._receive_buffer_port))

        return resources

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "tensorFlow_addition.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.SYNC

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        print("\n add_vertex generate_machine_data_specification")

        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, self.DATA_REGIONS.SYSTEM.value,
                                    self, machine_time_step, time_scale_factor)

        self.placement = placement

        self._reserve_memory_regions(spec)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.RECORDED_ADDITION_RESULT.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [4], self._time_between_requests,
             4 + 256, iptags))

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec):
        print("\n add_vertex _reserve_memory_regions")

        spec.reserve_memory_region(
            region=self.DATA_REGIONS.INPUT_CONST_VALUES.value,
            size=self.INPUT_DATA_SIZE, label="inputs_const_values")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RECORDED_ADDITION_RESULT.value,
            size=recording_utilities.get_recording_header_size(1),
            label="recorded_addition_result")

    # Kostas : read the data that are written in SDRAM
    def read(self, placement, buffer_manager):
        """ Get the data written into sdram

        :param placement: the location of this vertex
        :param buffer_manager: the buffer manager
        :return: string output
        """
        data_pointer, missing_data = buffer_manager.get_data_for_vertex(
            placement, 0)
        if missing_data:
            raise Exception("missing data!")
        return str(data_pointer.read_all())

    def get_minimum_buffer_sdram_usage(self):
        return self._string_data_size

    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        return recording_utilities.get_n_timesteps_in_buffer_space(
            buffer_space, 4)

    def get_recorded_region_ids(self):
        return [0]

    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RECORDED_ADDITION_RESULT.value, txrx)