# Copyright (c) 2016 The University of Manchester
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

from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM


class ConwayBasicCell(MachineVertex):
    """
    Cell which represents a cell within the 2d fabric.
    """

    @property
    def sdram_required(self):
        return ConstantSDRAM(0)
