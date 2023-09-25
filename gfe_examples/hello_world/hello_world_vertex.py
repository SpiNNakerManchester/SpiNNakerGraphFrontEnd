# Copyright (c) 2015 The University of Manchester
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
from spinn_front_end_common.utilities.constants import SYSTEM_BYTES_REQUIREMENT
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management.recording_utilities \
    import (
        get_recording_header_size)
from spinnaker_graph_front_end.utilities import SimulatorVertex

logger = FormatAdapter(logging.getLogger(__name__))


class DataRegions(IntEnum):
    SYSTEM = 0
    STRING_DATA = 1


class Channels(IntEnum):
    HELLO = 0


class HelloWorldVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):

    def __init__(self, n_hellos, label=None):
        super().__init__(label, "hello_world.aplx")

        self._string_data_size = n_hellos * 13

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        return ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT +
            get_recording_header_size(len(Channels)) +
            self._string_data_size)

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        # Generate the system data region for simulation .c requirements
        self.generate_system_region(spec)

        # Make the data regions for hello world; it's just a recording region
        self.generate_recording_region(
            spec, DataRegions.STRING_DATA, [self._string_data_size])

        # End-of-Spec:
        spec.end_specification()

    def read(self):
        """
        Get the data written into SDRAM.

        :return: string output
        """
        raw_data, missing_data = self.get_recording_channel_data(0)
        if missing_data:
            raise ValueError("missing data!")
        return str(bytearray(raw_data))

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [Channels.HELLO]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, placement):
        return locate_memory_region_for_placement(
            placement, DataRegions.STRING_DATA)
