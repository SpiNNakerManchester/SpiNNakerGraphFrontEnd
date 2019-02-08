import logging
from enum import Enum
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import (
    ConstantSDRAM, CPUCyclesPerTickResource, DTCMResource, ResourceContainer)
from spinn_front_end_common.utilities import (
    globals_variables, constants, helpful_functions)
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinn_front_end_common.utilities.utility_objs import ExecutableType

logger = logging.getLogger(__name__)


class HelloWorldVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        AbstractReceiveBuffersToHost):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('STRING_DATA', 1)])

    CORE_APP_IDENTIFIER = 0xBEEF

    def __init__(self, label, constraints=None):
        super(HelloWorldVertex, self).__init__(
            label=label, constraints=constraints)

        config = globals_variables.get_simulator().config
        self._buffer_size_before_receive = None
        if config.getboolean("Buffers", "enable_buffered_recording"):
            self._buffer_size_before_receive = config.getint(
                "Buffers", "buffer_size_before_receive")
        self._time_between_requests = config.getint(
            "Buffers", "time_between_requests")
        self._receive_buffer_host = config.get(
            "Buffers", "receive_buffer_host")
        self._receive_buffer_port = helpful_functions.read_config_int(
            config, "Buffers", "receive_buffer_port")

        self._string_data_size = 5000

        self.placement = None

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100), sdram=ConstantSDRAM(100))

        resources.extend(recording_utilities.get_recording_resources(
            [self._string_data_size],
            self._receive_buffer_host, self._receive_buffer_port))

        return resources

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "hello_world.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):
        self.placement = placement

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT

        # Reserve SDRAM space for memory areas:

        # Create the data regions for hello world
        self._reserve_memory_regions(spec, setup_size)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # recording data region
        spec.switch_write_focus(self.DATA_REGIONS.STRING_DATA.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [self._string_data_size], self._time_between_requests,
            self._string_data_size + 256, iptags))

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=system_size,
            label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.STRING_DATA.value,
            size=recording_utilities.get_recording_header_size(1),
            label="Recording")

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

    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        return recording_utilities.get_n_timesteps_in_buffer_space(
            buffer_space, len("Hello world"))

    def get_recorded_region_ids(self):
        return [0]

    def get_recording_region_base_address(self, txrx, placement):
        return helpful_functions.locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.STRING_DATA.value, txrx)
