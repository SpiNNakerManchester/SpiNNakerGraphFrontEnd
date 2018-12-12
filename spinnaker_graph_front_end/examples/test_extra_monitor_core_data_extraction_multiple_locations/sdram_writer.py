from enum import Enum

from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, SDRAMResource
from spinn_front_end_common.abstract_models import \
    AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities


class SDRAMWriter(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024*1024
    CONFIG_REGION_SIZE = 4

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1),
               ('DATA', 2)])

    def __init__(self, mbs, constraint):
        self._mbs = mbs * self.SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        MachineVertex.__init__(self, label="speed", constraints=[constraint])
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)

    @property
    def mbs_in_bytes(self):
        return self._mbs

    @property
    def resources_required(self):
        return ResourceContainer(sdram=SDRAMResource(
            self._mbs + constants.SYSTEM_BYTES_REQUIREMENT +
            self.CONFIG_REGION_SIZE))

    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

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

        spec.switch_write_focus(self.DATA_REGIONS.CONFIG.value)
        spec.write_value(self._mbs)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=system_size,
            label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.CONFIG.value,
            size=self.CONFIG_REGION_SIZE,
            label="config")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.DATA.value,
            size=self._mbs,
            label="data region")

    def get_binary_file_name(self):
        return "sdram_writer.aplx"
