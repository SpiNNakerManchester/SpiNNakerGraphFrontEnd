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
from pacman.model.resources import CPUCyclesPerTickResource, DTCMResource
from pacman.model.resources import ResourceContainer, VariableSDRAM
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

    def __init__(self, label, constraints=None):
        super().__init__(
            label=label, binary_name="c_template_vertex.aplx",
            constraints=constraints)

        # Set the recording size here
        self._recording_size = BYTES_PER_WORD

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        constant_sdram = (
            SYSTEM_BYTES_REQUIREMENT + self.TRANSMISSION_REGION_N_BYTES +
            recording_utilities.get_recording_header_size(
                len(RecordingChannels)) +
            recording_utilities.get_recording_data_constant_size(
                len(RecordingChannels)))
        variable_sdram = self.N_RECORDED_PER_TIMESTEP
        return ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100),
            sdram=VariableSDRAM(constant_sdram, variable_sdram))

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
        """ Get the recorded data

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
