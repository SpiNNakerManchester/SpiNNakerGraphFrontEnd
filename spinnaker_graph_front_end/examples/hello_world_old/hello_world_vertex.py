import logging
from enum import Enum
from spinn_utilities.overrides import overrides
from spinn_front_end_common.utilities.constants import SYSTEM_BYTES_REQUIREMENT
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import (
    CPUCyclesPerTickResource, DTCMResource, ResourceContainer, ConstantSDRAM)
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement, read_config_int)
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)

logger = logging.getLogger(__name__)

# Kostas: Here there is an inheritance from SimulatorVertex class.
class HelloWorldVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):

    # Kostas: These are the regions of SDRAM
    # Here you store the hello world message
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('STRING_DATA', 2)])

    PARTITION_ID = "TEST"

    TRANSMISSION_DATA_SIZE = 2 * 4  # has key and key
    CORE_APP_IDENTIFIER = 0xBEEF

    def __init__(self, label, constraints=None):
        super(HelloWorldVertex, self).__init__(
            label, "hello_world.aplx", constraints=constraints)

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

        self.placement = None

    # Kostas : This function returns the resources required by the vertex
    # from the spinnaker machine.
    @property
    @overrides(MachineVertex.resources_required)
    # Kostas :100 bytes only
    def resources_required(self):
        # resources = ResourceContainer(
        #     cpu_cycles=CPUCyclesPerTickResource(45),
        #     dtcm=DTCMResource(100), sdram=SDRAMResource(100))
        #
        # resources.extend(recording_utilities.get_recording_resources(
        #     [self._string_data_size],
        #     self._receive_buffer_host, self._receive_buffer_port))

        resources = ResourceContainer(sdram=ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT +
            recording_utilities.get_recording_header_size(1) +
            self._string_data_size))

        return resources

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, self.DATA_REGIONS.SYSTEM.value,
                                    self, machine_time_step, time_scale_factor)

        self.placement = placement

        # Reserve SDRAM space for memory areas:

        # reserve memory region
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_SIZE, label="inputs")

        # write key needed to transmit with
        # Kostas: in the initialization the keys get their values
        # otherwise the region of keys is empty in SDRAM and c code
        # will fail to read them.
        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)
        print("\n key is " ,key)
        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        spec.write_value(0 if key is None else 1)
        spec.write_value(0 if key is None else key)

        # Create the data regions for hello world
        self._reserve_memory_regions(spec)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.STRING_DATA.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [self._string_data_size]))

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.STRING_DATA.value,
            size=recording_utilities.get_recording_header_size(1),
            label="Recording")

    # Kostas : read the data that are written in SDRAM
    def read(self, placement, buffer_manager):
                #these "hello word" texts retrieved from every core .
        """ Get the data written into sdram

        :param placement: the location of this vertex
        :param buffer_manager: the buffer manager
        :return: string output
        """

        data_pointer, missing_data = buffer_manager.get_data_by_placement(
            placement, 0)
        if missing_data:
            raise Exception("missing data!")
        return str(data_pointer)

    # Kostas: Minimum SDRAM usage is 5000
    def get_minimum_buffer_sdram_usage(self):
        return self._string_data_size

    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        return recording_utilities.get_n_timesteps_in_buffer_space(
            buffer_space, len("Hello world"))

    def get_recorded_region_ids(self):
        return [0]

    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.STRING_DATA.value, txrx)
