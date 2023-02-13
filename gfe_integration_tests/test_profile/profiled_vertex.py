# Copyright (c) 2017-2023 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
