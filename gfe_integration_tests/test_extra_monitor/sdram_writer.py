# Copyright (c) 2017 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import IntEnum
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM
from spinn_front_end_common.abstract_models import (
    AbstractHasAssociatedBinary)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.constants import (
    SIMULATION_N_BYTES, SYSTEM_BYTES_REQUIREMENT, BYTES_PER_KB)

_SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024 * BYTES_PER_KB
_CONFIG_REGION_SIZE = 4


class DataRegions(IntEnum):
    SYSTEM = 0
    CONFIG = 1
    DATA = 2


class SDRAMWriter(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):
    def __init__(self, mebibytes):
        self._size = mebibytes * _SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        super().__init__(label="speed")

    @property
    def mbs_in_bytes(self):
        return self._size

    @property
    def sdram_required(self):
        return ConstantSDRAM(
            self._size + SYSTEM_BYTES_REQUIREMENT + _CONFIG_REGION_SIZE)

    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        # Reserve SDRAM space for memory areas:
        self._reserve_memory_regions(spec)

        # write data for the simulation data item
        spec.switch_write_focus(DataRegions.SYSTEM)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name()))

        spec.switch_write_focus(DataRegions.CONFIG)
        spec.write_value(self._size)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec):
        spec.reserve_memory_region(
            region=DataRegions.SYSTEM,
            size=SIMULATION_N_BYTES,
            label='systemInfo')
        spec.reserve_memory_region(
            region=DataRegions.CONFIG,
            size=_CONFIG_REGION_SIZE,
            label="config")
        spec.reserve_memory_region(
            region=DataRegions.DATA,
            size=self._size,
            label="data region")

    def get_binary_file_name(self):
        return "sdram_writer.aplx"
