# Copyright (c) 2017-2022 The University of Manchester
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

from enum import IntEnum
import logging
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM
from spinn_front_end_common.utilities.constants import SYSTEM_BYTES_REQUIREMENT
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.profiling import AbstractHasProfileData
from spinn_front_end_common.interface.profiling.profile_utils import (
    get_profile_region_size, reserve_profile_region, write_profile_region_data,
    get_profiling_data)
from spinnaker_graph_front_end.utilities import SimulatorVertex

logger = FormatAdapter(logging.getLogger(__name__))


class DataRegions(IntEnum):
    SYSTEM = 0
    PROFILE = 1


PROFILE_TAGS = {
    1: "SDRAMWrite",
    2: "DTCMWrite"
}

N_SAMPLES = 100


class ProfiledVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractHasProfileData):

    def __init__(self, label=None):
        super().__init__(label, "test_profile.aplx")

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        return ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT +
            get_profile_region_size(N_SAMPLES))

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        # Generate the system data region for simulation .c requirements
        self.generate_system_region(spec)

        # Do profile writing
        reserve_profile_region(spec, DataRegions.PROFILE.value, N_SAMPLES)
        write_profile_region_data(spec, DataRegions.PROFILE.value, N_SAMPLES)

        # End-of-Spec:
        spec.end_specification()

    @overrides(AbstractHasProfileData.get_profile_data)
    def get_profile_data(self, placement):
        return get_profiling_data(
            DataRegions.PROFILE.value, PROFILE_TAGS, placement)
