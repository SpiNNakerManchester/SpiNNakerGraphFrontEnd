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
import logging
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.abstract_models import (
    AbstractGeneratesDataSpecification, AbstractHasAssociatedBinary)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)
from pacman.model.graphs.application.abstract import (
    AbstractOneAppOneMachineVertex)

logger = FormatAdapter(logging.getLogger(__name__))


SEND_PARTITION = "send"


class DataRegions(IntEnum):
    SYSTEM = 0
    DATA = 1


class SyncTestVertex(AbstractOneAppOneMachineVertex):
    def __init__(self, lead, label=None):
        AbstractOneAppOneMachineVertex.__init__(
            self, SyncTestMachineVertex(lead, self, label),
            label, n_atoms=1)


class SyncTestMachineVertex(MachineVertex, AbstractHasAssociatedBinary,
                            AbstractGeneratesDataSpecification):
    def __init__(self, lead, app_vertex, label=None):
        super().__init__(label, app_vertex)
        self._lead = lead

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sync_test.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        return ConstantSDRAM(SYSTEM_BYTES_REQUIREMENT + BYTES_PER_WORD * 2)

    @overrides(
        AbstractGeneratesDataSpecification.generate_data_specification)
    def generate_data_specification(self, spec, placement):
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, DataRegions.SYSTEM.value, self)

        spec.reserve_memory_region(DataRegions.DATA.value, 2 * BYTES_PER_WORD)
        spec.switch_write_focus(DataRegions.DATA.value)
        spec.write_value(int(self._lead))
        if not self._lead:
            spec.write_value(0)
        else:
            routing_info = FecDataView.get_routing_infos()
            spec.write_value(routing_info.get_first_key_from_pre_vertex(
                self, SEND_PARTITION))

        # End-of-Spec:
        spec.end_specification()
