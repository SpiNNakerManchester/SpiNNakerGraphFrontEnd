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

from enum import IntEnum
import logging
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import VariableSDRAM
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinnaker_graph_front_end.utilities import SimulatorVertex

logger = FormatAdapter(logging.getLogger(__name__))

PARTITION_ID = "DATA"


# TODO: Update with the regions of the application
class DataRegions(IntEnum):
    SYSTEM = 0
    TRANSMISSION = 1
    RECORDED_DATA = 2


# TODO: Update with the recording channels of the application
class RecordingChannels(IntEnum):
    RECORDING = 0


class TemplateVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):
    # pylint: disable=unused-argument

    # The number of bytes for the has_key flag and the key
    TRANSMISSION_REGION_N_BYTES = 2 * BYTES_PER_WORD

    # The number of bytes recorded per timestep - currently 0 in C code
    N_RECORDED_PER_TIMESTEP = 0

    def __init__(self, label):
        super().__init__(
            label=label, binary_name="c_template_vertex.aplx")

        # Set the recording size here
        self._recording_size = BYTES_PER_WORD

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        constant_sdram = (
            SYSTEM_BYTES_REQUIREMENT + self.TRANSMISSION_REGION_N_BYTES +
            recording_utilities.get_recording_header_size(
                len(RecordingChannels)) +
            recording_utilities.get_recording_data_constant_size(
                len(RecordingChannels)))
        variable_sdram = self.N_RECORDED_PER_TIMESTEP
        return VariableSDRAM(constant_sdram, variable_sdram)

    # remember to override iptags and/or reverse_iptags if required

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        # Generate the system data region for simulation .c requirements
        self.generate_system_region(spec, DataRegions.SYSTEM)

        # Generate the application data regions
        self._reserve_app_memory_regions(spec)
        self._write_app_memory_regions(spec, iptags)

        # Generate the recording region
        self.generate_recording_region(
            spec, DataRegions.RECORDED_DATA, [self._recording_size])

        # End-of-Spec:
        spec.end_specification()

    def _reserve_app_memory_regions(self, spec):
        spec.reserve_memory_region(
            region=DataRegions.TRANSMISSION,
            size=self.TRANSMISSION_REGION_N_BYTES, label="transmission")

    def _write_app_memory_regions(self, spec, iptags):
        # Get the key, assuming all outgoing edges use the same key
        routing_info = FecDataView.get_routing_infos()
        key = routing_info.get_first_key_from_pre_vertex(self, PARTITION_ID)

        # Write the transmission region
        spec.switch_write_focus(DataRegions.TRANSMISSION)
        spec.write_value(int(key is not None))
        spec.write_value(0 if key is None else key)

    def read(self):
        """
        Get the recorded data.

        :return: The data read, as bytes
        """
        raw_data, is_missing_data = self.get_recording_channel_data(
            RecordingChannels.RECORDING)
        if is_missing_data:
            logger.warning("Some data was lost when recording")
        return raw_data

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [RecordingChannels.RECORDING]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, placement):
        return locate_memory_region_for_placement(
            placement, DataRegions.RECORDED_DATA)
