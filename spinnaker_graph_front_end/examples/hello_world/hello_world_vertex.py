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
import logging
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, ConstantSDRAM
from spinn_front_end_common.utilities.constants import SYSTEM_BYTES_REQUIREMENT
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)

logger = logging.getLogger(__name__)


class HelloWorldVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('STRING_DATA', 1)])

    def __init__(self, label=None, constraints=None):
        super(HelloWorldVertex, self).__init__(
            label, "hello_world.aplx", constraints=constraints)

        self._string_data_size = 5000

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        resources = ResourceContainer(sdram=ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT +
            recording_utilities.get_recording_header_size(1) +
            self._string_data_size))

        return resources

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, time_scale_factor):
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, self.DATA_REGIONS.SYSTEM.value,
                                    self, time_scale_factor)

        # Reserve SDRAM space for memory areas:

        # Create the data regions for hello world
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.STRING_DATA.value,
            size=recording_utilities.get_recording_header_size(1),
            label="Recording")

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.STRING_DATA.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [self._string_data_size]))

        # End-of-Spec:
        spec.end_specification()

    def read(self, placement, buffer_manager):
        """ Get the data written into SDRAM

        :param placement: the location of this vertex
        :param buffer_manager: the buffer manager
        :return: string output
        """
        raw_data, missing_data = buffer_manager.get_data_by_placement(
            placement, 0)
        if missing_data:
            raise Exception("missing data!")
        return str(bytearray(raw_data))

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [0]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.STRING_DATA.value, txrx)
