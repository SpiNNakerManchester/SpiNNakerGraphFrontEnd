from pacman.model.decorators.overrides import overrides
from spinn_front_end_common.abstract_models\
    .abstract_binary_uses_simulation_run import AbstractBinaryUsesSimulationRun
from pacman.model.graphs.machine.impl.machine_vertex \
    import MachineVertex
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.sdram_resource import SDRAMResource

from spinn_front_end_common.interface.buffer_management.\
    buffer_models.receives_buffers_to_host_basic_impl import \
    ReceiveBuffersToHostBasicImpl
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.abstract_models.impl.machine_data_specable_vertex \
    import MachineDataSpecableVertex
from spinn_front_end_common.abstract_models.abstract_has_associated_binary \
    import AbstractHasAssociatedBinary

from spinnaker_graph_front_end.utilities.conf import config

from enum import Enum

import logging

logger = logging.getLogger(__name__)


class HelloWorldVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        ReceiveBuffersToHostBasicImpl, AbstractBinaryUsesSimulationRun):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('STRING_DATA', 1),
               ('BUFFERED_STATE', 2)])

    CORE_APP_IDENTIFIER = 0xBEEF

    def __init__(self, label, machine_time_step, time_scale_factor,
                 constraints=None):

        resources = ResourceContainer(cpu_cycles=CPUCyclesPerTickResource(45),
                                      dtcm=DTCMResource(100),
                                      sdram=SDRAMResource(100))

        MachineVertex.__init__(
            self, label=label, resources_required=resources,
            constraints=constraints)
        ReceiveBuffersToHostBasicImpl.__init__(self)

        self._buffer_size_before_receive = config.getint(
            "Buffers", "buffer_size_before_receive")

        self._time_between_requests = config.getint(
            "Buffers", "time_between_requests")

        self._string_data_size = 5000

        self.placement = None

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "hello_world.aplx"

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):
        self.placement = placement

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT + 8

        # Reserve SDRAM space for memory areas:

        # Create the data regions for hello world
        self._reserve_memory_regions(spec, setup_size)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # recording data region
        self.write_recording_data(
            spec, iptags, [self._string_data_size],
            self._buffer_size_before_receive, self._time_between_requests)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(region=self.DATA_REGIONS.SYSTEM.value,
                                   size=system_size, label='systemInfo')
        self.reserve_buffer_regions(
            spec, self.DATA_REGIONS.BUFFERED_STATE.value,
            [self.DATA_REGIONS.STRING_DATA.value],
            [self._string_data_size])

    def read(self, placement, buffer_manager):
        """ Get the data written into sdram

        :param placement: the location of this vertex
        :param buffer_manager: the buffer manager
        :return: string output
        """
        data_pointer, missing_data = buffer_manager.get_data_for_vertex(
            placement, self.DATA_REGIONS.STRING_DATA.value,
            self.DATA_REGIONS.BUFFERED_STATE.value)
        if missing_data:
            raise Exception("missing data!")
        record_raw = data_pointer.read_all()
        output = str(record_raw)
        return output
