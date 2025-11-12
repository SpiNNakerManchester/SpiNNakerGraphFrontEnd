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
from typing import Iterable, List, Optional, Set
from spinn_utilities.overrides import overrides
from spinn_machine.tags import IPTag, ReverseIPTag
from pacman.model.graphs.machine import MachineVertex
from pacman.model.placements import Placement
from pacman.model.resources import VariableSDRAM
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.interface.ds import DataSpecificationGenerator
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement, n_word_struct)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
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


class ConwayBasicCell(SimulatorVertex, MachineDataSpecableVertex):
    """
    Cell which represents a cell within the 2d fabric.
    """

    PARTITION_ID = "STATE"

    TRANSMISSION_DATA_SIZE = 2 * BYTES_PER_WORD  # has key and key
    STATE_DATA_SIZE = 1 * BYTES_PER_WORD  # 1 or 2 based off dead or alive
    # alive states, dead states
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * BYTES_PER_WORD
    # The size of the size of the recording(!)
    RECORDING_HEADER_SIZE = BYTES_PER_WORD
    RECORDING_ELEMENT_SIZE = STATE_DATA_SIZE  # A recording of the state

    def __init__(self, label: str, state: bool):
        """
        :param label:
        :param state:
        """
        super().__init__(label, "conways_cell.aplx")

        # app specific data items
        self._state = bool(state)
        self._neighbours: Set[ConwayBasicCell] = set()

    def add_neighbour(self, neighbour: "ConwayBasicCell") -> None:
        if neighbour == self:
            raise ValueError("Cannot add self as neighbour!")
        self._neighbours.add(neighbour)

    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec: DataSpecificationGenerator, placement: Placement,
            iptags: Optional[Iterable[IPTag]],
            reverse_iptags: Optional[Iterable[ReverseIPTag]]) -> None:
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
        spec.reserve_memory_region(
            region=DataRegions.RESULTS,
            size=(self.RECORDING_HEADER_SIZE +
                  (FecDataView.get_max_run_time_steps() *
                   self.RECORDING_ELEMENT_SIZE)),
            label="results")

        # write key needed to transmit with
        r_infos = FecDataView.get_routing_infos()
        key = r_infos.get_single_machine_key(self)

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

    def get_data(self) -> List[bool]:
        txrx = FecDataView.get_transceiver()
        placement = self.placement
        n_steps = FecDataView.get_current_run_timesteps()
        assert n_steps is not None
        # Get the data region base address where results are stored for the
        # core
        record_region_base_address = locate_memory_region_for_placement(
            placement, DataRegions.RESULTS)

        # find how many bytes are needed to be read
        number_of_bytes_to_read = txrx.read_word(
            placement.x, placement.y, record_region_base_address)
        expected_bytes = n_steps * self.RECORDING_ELEMENT_SIZE
        if number_of_bytes_to_read != expected_bytes:
            raise ConfigurationException(
                f"number of bytes seems wrong; have {number_of_bytes_to_read} "
                f"but expected {expected_bytes}")

        # read the bytes
        raw_data = txrx.read_memory(
            placement.x, placement.y,
            record_region_base_address + self.RECORDING_HEADER_SIZE,
            number_of_bytes_to_read)

        # convert to booleans
        return [bool(element) for element in
                n_word_struct(n_steps).unpack(raw_data)]

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self) -> VariableSDRAM:
        fixed_sdram = (SYSTEM_BYTES_REQUIREMENT + self.TRANSMISSION_DATA_SIZE +
                       self.STATE_DATA_SIZE +
                       self.NEIGHBOUR_INITIAL_STATES_SIZE +
                       self.RECORDING_HEADER_SIZE)
        per_timestep_sdram = self.RECORDING_ELEMENT_SIZE
        return VariableSDRAM(fixed_sdram, per_timestep_sdram)

    @property
    def state(self) -> bool:
        return self._state

    def __repr__(self) -> str:
        return str(self.label)
