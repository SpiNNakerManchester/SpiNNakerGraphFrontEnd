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
from typing import List, Optional
from spinn_utilities.overrides import overrides
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import MachineVertex, SDRAMMachineEdge
from pacman.model.partitioner_splitters import AbstractSplitterCommon
from pacman.model.graphs.machine import SourceSegmentedSDRAMMachinePartition
from pacman.utilities.utility_objs import ChipCounter

from gfe_integration_tests.sdram_edge_tests.common import SDRAMMachineVertex


class SDRAMSplitter(AbstractSplitterCommon):
    """ sdram splitter
    """

    N_VERTS = 3

    __slots__ = [
        "_pre_vertices",
        "__post_vertex",
        "_partition"]

    def __init__(self) -> None:
        super().__init__()
        self.__post_vertex: Optional[SDRAMMachineVertex] = None
        self._pre_vertices: List[SDRAMMachineVertex] = list()

    @property
    def _post_vertex(self) -> SDRAMMachineVertex:
        assert isinstance(self.__post_vertex, SDRAMMachineVertex)
        return self.__post_vertex

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(
            self, partition_id: str) -> List[MachineVertex]:
        assert isinstance(self.__post_vertex, SDRAMMachineVertex)
        return [self.__post_vertex]

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(
            self, partition_id: str) -> List[SDRAMMachineVertex]:
        return self._pre_vertices

    @overrides(AbstractSplitterCommon.create_machine_vertices)
    def create_machine_vertices(self, chip_counter: ChipCounter) -> None:
        # slices
        post_slice = Slice(
            0, int(self.governed_app_vertex.n_atoms / self.N_VERTS))

        pre_slices = list()
        for count in range(1, self.N_VERTS):
            pre_slices.append(Slice(
                post_slice.n_atoms * count,
                post_slice.n_atoms * count + post_slice.n_atoms))

        # mac verts
        self.__post_vertex = SDRAMMachineVertex(
            vertex_slice=post_slice, label=None,
            app_vertex=self.governed_app_vertex)
        self.governed_app_vertex.remember_machine_vertex(self._post_vertex)

        for vertex_slice in pre_slices:
            pre_vertex = SDRAMMachineVertex(
                vertex_slice=vertex_slice, label=None,
                app_vertex=self.governed_app_vertex, sdram_cost=20)
            self.governed_app_vertex.remember_machine_vertex(pre_vertex)
            self._pre_vertices.append(pre_vertex)

        self._partition = SourceSegmentedSDRAMMachinePartition(
            identifier="sdram", pre_vertices=self._pre_vertices)
        self._post_vertex.add_incoming_sdram_partition(self._partition)
        chip_counter.add_core(self._post_vertex.sdram_required)
        for pre_vertex in self._pre_vertices:
            edge = SDRAMMachineEdge(
                pre_vertex, self._post_vertex, label="sdram")
            self._partition.add_edge(edge)
            pre_vertex.add_outgoing_sdram_partition(self._partition)
            chip_counter.add_core(pre_vertex.sdram_required)

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self) -> List[Slice]:
        return [self._post_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self) -> List[Slice]:
        return [v.vertex_slice for v in self._pre_vertices]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(
            self, variable_to_record: str) -> List[MachineVertex]:
        mv: List[MachineVertex] = [self._post_vertex]
        mv.extend(self._pre_vertices)
        return mv


    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self) -> None:
        pass

    @overrides(AbstractSplitterCommon.get_internal_sdram_partitions)
    def get_internal_sdram_partitions(
            self) -> List[SourceSegmentedSDRAMMachinePartition]:
        assert isinstance(
            self._partition, SourceSegmentedSDRAMMachinePartition)
        return [self._partition]
