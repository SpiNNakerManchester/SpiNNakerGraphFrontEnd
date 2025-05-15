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
from pacman.model.graphs.machine import (
    SDRAMMachineEdge, DestinationSegmentedSDRAMMachinePartition)
from pacman.model.partitioner_splitters import AbstractSplitterCommon
from gfe_integration_tests.sdram_edge_tests.common import SDRAMMachineVertex


class SDRAMSplitter(AbstractSplitterCommon):
    """ sdram splitter
    """

    N_VERTS = 3

    __slots__ = [
        "__pre_vertex",
        "_post_vertices",
        "_partition"]

    def __init__(self) -> None:
        super().__init__()
        self.__pre_vertex = None
        self._post_vertices: List[SDRAMMachineVertex] = list()

    @property
    def _pre_vertex(self) -> SDRAMMachineVertex:
        assert isinstance(self.__pre_vertex, SDRAMMachineVertex)
        return self.__pre_vertex

    @property
    def __post_vertex(self) -> None:
        assert isinstance(self.__post_vertex, SDRAMMachineVertex)
        return self.__post_vertex

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(self, partition_id: str) -> List[SDRAMMachineVertex]:
        return self._post_vertices

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(self, partition_id: str) -> List[SDRAMMachineVertex]:
        return [self._pre_vertex]

    def create_machine_vertices(self, chip_counter):
        # slices
        pre_slice = Slice(
            0, int(self.governed_app_vertex.n_atoms / self.N_VERTS))

        post_slices = list()
        for count in range(1, self.N_VERTS):
            post_slices.append(Slice(
                pre_slice.n_atoms * count,
                pre_slice.n_atoms * count + pre_slice.n_atoms))

        # mac verts
        self.__pre_vertex = SDRAMMachineVertex(
            vertex_slice=pre_slice, label=None,
            app_vertex=self.governed_app_vertex, sdram_cost=20)
        self.governed_app_vertex.remember_machine_vertex(self._pre_vertex)

        for vertex_slice in post_slices:
            post_vertex = SDRAMMachineVertex(
                vertex_slice=vertex_slice, label=None,
                app_vertex=self.governed_app_vertex)
            self._post_vertices.append(post_vertex)
            self.governed_app_vertex.remember_machine_vertex(post_vertex)

        self._partition = DestinationSegmentedSDRAMMachinePartition(
            identifier="sdram", pre_vertex=self._pre_vertex)
        self._pre_vertex.add_outgoing_sdram_partition(self._partition)
        for post_vertex in self._post_vertices:
            edge = SDRAMMachineEdge(
                self._pre_vertex, post_vertex, label="sdram")
            self._partition.add_edge(edge)
            post_vertex.add_incoming_sdram_partition(self._partition)
            chip_counter.add_core(post_vertex.sdram_required)

        chip_counter.add_core(self._pre_vertex.sdram_required)
        return 1

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self) -> List[Slice]:
        return [v.vertex_slice for v in self._post_vertices]

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self) -> List[Slice]:
        return [self._pre_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(
            self, variable_to_record: str) -> List[SDRAMMachineVertex]:
        mv = [self._pre_vertex]
        mv.extend(self._post_vertices)
        return mv

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self) -> None:
        pass

    @overrides(AbstractSplitterCommon.get_internal_sdram_partitions)
    def get_internal_sdram_partitions(
            self) -> List[DestinationSegmentedSDRAMMachinePartition]:
        assert isinstance(
            self._partition, DestinationSegmentedSDRAMMachinePartition)
        return [self._partition]
