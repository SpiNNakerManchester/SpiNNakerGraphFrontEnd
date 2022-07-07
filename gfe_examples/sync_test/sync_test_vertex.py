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

from enum import IntEnum
import logging
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.executor.injection_decorator import inject_items
from pacman.model.resources import ResourceContainer, ConstantSDRAM
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

    def __init__(self, lead, label=None, constraints=None):
        AbstractOneAppOneMachineVertex.__init__(
            self, SyncTestMachineVertex(lead, self, label, constraints),
            label, None, n_atoms=1)


class SyncTestMachineVertex(MachineVertex, AbstractHasAssociatedBinary,
                            AbstractGeneratesDataSpecification):

    def __init__(self, lead, app_vertex, label=None, constraints=None):
        super().__init__(label, constraints, app_vertex)
        self._lead = lead

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sync_test.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(sdram=ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT + BYTES_PER_WORD * 2))

        return resources

    @inject_items({"routing_info": "RoutingInfos"})
    @overrides(
        AbstractGeneratesDataSpecification.generate_data_specification,
        additional_arguments={"routing_info"})
    def generate_data_specification(self, spec, placement, routing_info):
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, DataRegions.SYSTEM.value, self)

        spec.reserve_memory_region(DataRegions.DATA.value, 2 * BYTES_PER_WORD)
        spec.switch_write_focus(DataRegions.DATA.value)
        spec.write_value(int(self._lead))
        if not self._lead:
            spec.write_value(0)
        else:
            spec.write_value(routing_info.get_first_key_from_pre_vertex(
                self, SEND_PARTITION))

        # End-of-Spec:
        spec.end_specification()
