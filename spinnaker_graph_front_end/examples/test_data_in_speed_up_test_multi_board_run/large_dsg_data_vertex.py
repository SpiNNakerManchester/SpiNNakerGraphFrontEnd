import numpy

from pacman.model.decorators import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import CPUCyclesPerTickResource, DTCMResource
from pacman.model.resources import ResourceContainer, SDRAMResource

from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.abstract_models.impl \
    import MachineDataSpecableVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities.utility_objs import ExecutableType

from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class LargeDSGDataVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('LARGE_DATA', 1),
               ('SIZE_OF_DATA', 2)])

    CORE_APP_IDENTIFIER = 0xBEEF

    def __init__(self, size_of_dsg_region, constraints=None):
        MachineVertex.__init__(
            self, label="large dsg vertex", constraints=constraints)
        self._size_of_dsg_region = size_of_dsg_region

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100),
            sdram=SDRAMResource(
                self._size_of_dsg_region + constants.SYSTEM_BYTES_REQUIREMENT +
                4))
        return resources

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sdram_reader.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        # Create the data regions
        self._reserve_memory_regions(spec)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # write large data
        spec.switch_write_focus(self.DATA_REGIONS.LARGE_DATA.value)
        iterations = int(math.floor(self._size_of_dsg_region / 4))

        spec.write_array(numpy.arange(
            start=0, stop=self._size_of_dsg_region / 4, step=1,
            dtype="uint32"))

        # write iterations size for c code to know
        spec.switch_write_focus(self.DATA_REGIONS.SIZE_OF_DATA.value)
        spec.write_value(iterations)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value,
            size=constants.SYSTEM_BYTES_REQUIREMENT,
            label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.LARGE_DATA.value,
            size=self._size_of_dsg_region, label="large data store")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SIZE_OF_DATA.value,
            size=4, label="data pointer")
