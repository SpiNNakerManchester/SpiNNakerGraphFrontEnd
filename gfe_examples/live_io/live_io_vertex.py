# Copyright (c) 2023 The University of Manchester
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
from typing import Iterable, Optional
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from spinn_machine.tags import IPTag, ReverseIPTag
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import MachineVertex
from pacman.model.placements import Placement
from pacman.model.resources import ConstantSDRAM
from spinn_front_end_common.interface.ds import DataSpecificationGenerator
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.data.fec_data_view import FecDataView
from spinnaker_graph_front_end.utilities import SimulatorVertex

logger = FormatAdapter(logging.getLogger(__name__))
N_KEY_DATA_BYTES = 3 * BYTES_PER_WORD


class DataRegions(IntEnum):
    SYSTEM = 0
    KEY_DATA = 1


class LiveIOVertex(
        SimulatorVertex, MachineDataSpecableVertex):

    def __init__(self, n_keys: int, send_partition: str = "LiveOut",
                 label: Optional[str] = None):
        super().__init__(
            label, "live_io.aplx", vertex_slice=Slice(0, n_keys - 1))
        self.__n_keys = n_keys
        self.__send_partition = send_partition

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self) -> ConstantSDRAM:
        return ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT + N_KEY_DATA_BYTES)

    @overrides(SimulatorVertex.get_n_keys_for_partition)
    def get_n_keys_for_partition(self, partition_id: str) -> int:
        return self.__n_keys

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec: DataSpecificationGenerator, placement: Placement,
            iptags: Optional[Iterable[IPTag]],
            reverse_iptags: Optional[Iterable[ReverseIPTag]]) -> None:
        # Generate the system data region for simulation .c requirements
        self.generate_system_region(spec)

        spec.reserve_memory_region(DataRegions.KEY_DATA, N_KEY_DATA_BYTES)
        spec.switch_write_focus(DataRegions.KEY_DATA)

        routing_infos = FecDataView().get_routing_infos()
        r_info = routing_infos.get_single_info_from(
            placement.vertex)
        if r_info is None:
            spec.write_value(0)
            spec.write_value(0)
            spec.write_value(0)
        else:
            spec.write_value(1)
            spec.write_value(r_info.key)
            spec.write_value((~r_info.mask) & 0xFFFFFFFF)

        # End-of-Spec:
        spec.end_specification()
