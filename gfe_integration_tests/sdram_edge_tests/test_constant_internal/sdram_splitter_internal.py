# Copyright (c) 2020 The University of Manchester
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
from typing import List
from spinn_utilities.overrides import overrides
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import SDRAMMachineEdge
from pacman.model.partitioner_splitters import AbstractSplitterCommon
from pacman.model.graphs.machine import ConstantSDRAMMachinePartition
from gfe_integration_tests.sdram_edge_tests.common.\
    sdram_machine_vertex import SDRAMMachineVertex


class SDRAMSplitterInternal(AbstractSplitterCommon):
    """ sdram splitter
    """

    __slots__ = [
        "__pre_vertex",
        "__post_vertex",
        "_sdram_part"]

    def __init__(self):
        super().__init__()
        self.__pre_vertex = None
        self.__post_vertex = None
        self._sdram_part = None

    @property
    def _pre_vertex(self) -> SDRAMMachineVertex:
        assert isinstance(self.__pre_vertex, SDRAMMachineVertex)
        return self.__pre_vertex

    @property
    def _post_vertex(self):
        assert isinstance(self.__post_vertex, SDRAMMachineVertex)
        return self.__post_vertex

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(self, partition_id) -> List[SDRAMMachineVertex]:
        return [self._pre_vertex]

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(self, partition_id) -> list[SDRAMMachineVertex]:
        return [self._post_vertex]

    def create_machine_vertices(self, chip_counter):
        # slices
        pre_slice = Slice(0, int(self.governed_app_vertex.n_atoms / 2))
        post_slice = Slice(
            int(self.governed_app_vertex.n_atoms / 2) + 1,
            int(self.governed_app_vertex.n_atoms - 1))

        # mac verts
        self.__pre_vertex = SDRAMMachineVertex(
            vertex_slice=pre_slice, label=None,
            app_vertex=self.governed_app_vertex, sdram_cost=20)
        self.governed_app_vertex.remember_machine_vertex(self._pre_vertex)
        self.__post_vertex = SDRAMMachineVertex(
            vertex_slice=post_slice, label=None,
            app_vertex=self.governed_app_vertex)
        self.governed_app_vertex.remember_machine_vertex(self._post_vertex)

        self._sdram_part = ConstantSDRAMMachinePartition(
            identifier="sdram", pre_vertex=self._pre_vertex)
        self._sdram_part.add_edge(SDRAMMachineEdge(
            self._pre_vertex, self._post_vertex, label="sdram"))
        self._pre_vertex.add_outgoing_sdram_partition(self._sdram_part)
        self._post_vertex.add_incoming_sdram_partition(self._sdram_part)

        chip_counter.add_core(self._pre_vertex.sdram_required)
        chip_counter.add_core(self._post_vertex.sdram_required)

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self) -> List[Slice]:
        return [self._post_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self) -> List[Slice]:
        return [self._pre_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(
            self, variable_to_record: str) -> List[SDRAMMachineVertex]:
        return [self._pre_vertex, self._post_vertex]

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self) -> None:
        pass

    @overrides(AbstractSplitterCommon.get_internal_sdram_partitions)
    def get_internal_sdram_partitions(
            self) -> List[ConstantSDRAMMachinePartition]:
        assert isinstance(self._sdram_part, ConstantSDRAMMachinePartition)
        return [self._sdram_part]
