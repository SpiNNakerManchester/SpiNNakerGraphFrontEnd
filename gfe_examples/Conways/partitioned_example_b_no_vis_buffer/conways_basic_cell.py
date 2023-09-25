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
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import VariableSDRAM
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement, n_word_struct)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management.recording_utilities\
    import (
        get_recording_data_constant_size, get_recording_header_size)
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)


# Regions for populations
class DataRegions(IntEnum):
    SYSTEM = 0
    TRANSMISSIONS = 1
    STATE = 2
    NEIGHBOUR_INITIAL_STATES = 3
    RESULTS = 4


# Channels for doing recording in
class Channels(IntEnum):
    STATE_LOG = 0


class ConwayBasicCell(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):
    """
    Cell which represents a cell within the 2d fabric.
    """

    PARTITION_ID = "STATE"

    TRANSMISSION_DATA_SIZE = 2 * BYTES_PER_WORD  # has key and key
    STATE_DATA_SIZE = 1 * BYTES_PER_WORD  # 0 or 1 based off dead or alive
    # alive states, dead states
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * BYTES_PER_WORD
    RECORDING_ELEMENT_SIZE = STATE_DATA_SIZE  # A recording of the state

    def __init__(self, label, state):
        """
        :param str label:
        :param bool state:
        """
        super().__init__(label, "conways_cell.aplx")

        # app specific data items
        self._state = bool(state)
        self._neighbours = set()

    def add_neighbour(self, neighbour):
        if neighbour == self:
            raise ValueError("Cannot add self as neighbour!")
        self._neighbours.add(neighbour)

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        # pylint: disable=arguments-differ
        if len(self._neighbours) != 8:
            raise ValueError(
                f"Only {len(self._neighbours)} neighbours, not 8")

        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, DataRegions.SYSTEM, self)

        # reserve memory regions
        spec.reserve_memory_region(
            region=DataRegions.TRANSMISSIONS,
            size=self.TRANSMISSION_DATA_SIZE, label="inputs")
        spec.reserve_memory_region(
            region=DataRegions.STATE,
            size=self.STATE_DATA_SIZE, label="state")
        spec.reserve_memory_region(
            region=DataRegions.NEIGHBOUR_INITIAL_STATES,
            size=self.NEIGHBOUR_INITIAL_STATES_SIZE, label="neighour_states")

        # get recorded buffered regions sorted
        self.generate_recording_region(
            spec, DataRegions.RESULTS,
            [self.RECORDING_ELEMENT_SIZE *
             FecDataView.get_max_run_time_steps()])

        # write key needed to transmit with
        key = FecDataView.get_routing_infos().get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)

        spec.switch_write_focus(DataRegions.TRANSMISSIONS)
        spec.write_value(int(key is not None))
        spec.write_value(0 if key is None else key)

        # write state value
        spec.switch_write_focus(DataRegions.STATE)
        spec.write_value(int(bool(self._state)))

        # write neighbours data state
        spec.switch_write_focus(DataRegions.NEIGHBOUR_INITIAL_STATES)
        alive = sum(n.state for n in self._neighbours)
        dead = sum(not n.state for n in self._neighbours)
        spec.write_value(alive)
        spec.write_value(dead)

        # End-of-Spec:
        spec.end_specification()

    def get_data(self):
        # for buffering output info is taken form the buffer manager
        # get raw data, convert to list of booleans
        raw_data, data_missing = self.get_recording_channel_data(
            Channels.STATE_LOG)

        # do check for missing data
        if data_missing:
            placement = self.placement
            print("missing_data from "
                  f"({placement.x}, {placement.y}, {placement.p}); ")

        # return the data, converted to list of booleans
        return [
            bool(element) for element in
            n_word_struct(len(raw_data) // BYTES_PER_WORD).unpack(raw_data)]

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        fixed_sdram = (
            SYSTEM_BYTES_REQUIREMENT +
            self.TRANSMISSION_DATA_SIZE +
            self.STATE_DATA_SIZE +
            self.NEIGHBOUR_INITIAL_STATES_SIZE +
            get_recording_header_size(len(Channels)) +
            get_recording_data_constant_size(len(Channels)))
        per_timestep_sdram = self.RECORDING_ELEMENT_SIZE
        return VariableSDRAM(fixed_sdram, per_timestep_sdram)

    @property
    def state(self):
        return self._state

    def __repr__(self):
        return self.label

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [Channels.STATE_LOG]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, placement):
        return locate_memory_region_for_placement(
            placement, DataRegions.RESULTS)
