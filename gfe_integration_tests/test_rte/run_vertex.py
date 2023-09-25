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

from pacman.model.graphs.machine import SimpleMachineVertex
from pacman.model.resources import ConstantSDRAM
from spinn_front_end_common.abstract_models import (
    AbstractHasAssociatedBinary, AbstractGeneratesDataSpecification)
from spinn_front_end_common.interface.simulation import (
    simulation_utilities as
    utils)
from spinn_front_end_common.utilities.constants import SIMULATION_N_BYTES


class RunVertex(
        SimpleMachineVertex, AbstractHasAssociatedBinary,
        AbstractGeneratesDataSpecification):

    def __init__(self, aplx_file, executable_type):
        super().__init__(ConstantSDRAM(0))
        self._aplx_file = aplx_file
        self._executable_type = executable_type

    def get_binary_file_name(self):
        return self._aplx_file

    def get_binary_start_type(self):
        return self._executable_type

    def generate_data_specification(self, spec, placement):
        spec.reserve_memory_region(0, SIMULATION_N_BYTES)
        spec.switch_write_focus(0)
        spec.write_array(utils.get_simulation_header_array(self._aplx_file))
        spec.end_specification()
