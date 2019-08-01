# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from enum import Enum
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, ConstantSDRAM
from spinn_front_end_common.abstract_models import (
    AbstractHasAssociatedBinary)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.constants import SIMULATION_N_BYTES


class SDRAMWriter(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024*1024
    CONFIG_REGION_SIZE = 4

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1),
               ('DATA', 2)])

    def __init__(self, mbs):
        self._mbs = mbs * self.SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        super(SDRAMWriter, self).__init__(label="speed", constraints=None)

    @property
    def mbs_in_bytes(self):
        return self._mbs

    @property
    def resources_required(self):
        return ResourceContainer(sdram=ConstantSDRAM(
            self._mbs + constants.SYSTEM_BYTES_REQUIREMENT +
            self.CONFIG_REGION_SIZE))

    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        # Reserve SDRAM space for memory areas:
        self._reserve_memory_regions(spec)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        spec.switch_write_focus(self.DATA_REGIONS.CONFIG.value)
        spec.write_value(self._mbs)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=SIMULATION_N_BYTES,
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
