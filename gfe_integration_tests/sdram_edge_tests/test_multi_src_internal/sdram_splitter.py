# Copyright (c) 2020-2021 The University of Manchester
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
from gfe_integration_tests.sdram_edge_tests.common import SDRAMMachineVertex
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import SDRAMMachineEdge
from pacman.model.partitioner_splitters.abstract_splitters import (
    AbstractSplitterCommon)
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import SourceSegmentedSDRAMMachinePartition


class SDRAMSplitter(AbstractSplitterCommon):
    """ sdram splitter
    """

    N_VERTS = 3

    __slots__ = [
        "_pre_vertices",
        "_pre_slices",
        "_post_slice",
        "_post_vertex",
        "_partition"]

    def __init__(self):
        super().__init__()
        self._pre_vertices = list()
        self._post_vertex = None
        self._pre_slices = list()
        self._post_slice = None

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(self, partition_id):
        return [self._post_vertex]

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(self, partition_id):
        return self._pre_vertices

    def create_machine_vertices(self, chip_counter):

        # slices
        self._post_slice = Slice(
            0, int(self._governed_app_vertex.n_atoms / self.N_VERTS))

        for count in range(1, self.N_VERTS):
            self._pre_slices.append(Slice(
                self._post_slice.n_atoms * count,
                self._post_slice.n_atoms * count + self._post_slice.n_atoms))

        # mac verts
        self._post_vertex = (
            SDRAMMachineVertex(
                vertex_slice=self._post_slice, label=None,
                constraints=None, app_vertex=self._governed_app_vertex))
        self._governed_app_vertex.remember_machine_vertex(self._post_vertex)

        for vertex_slice in self._pre_slices:
            pre_vertex = (
                SDRAMMachineVertex(
                    vertex_slice=vertex_slice, label=None,
                    constraints=None, app_vertex=self._governed_app_vertex,
                    sdram_cost=20))
            self._governed_app_vertex.remember_machine_vertex(pre_vertex)
            self._pre_vertices.append(pre_vertex)

        self._partition = SourceSegmentedSDRAMMachinePartition(
            identifier="sdram", pre_vertices=self._pre_vertices)
        self._post_vertex.add_incoming_sdram_partition(self._partition)
        chip_counter.add_core(self._post_vertex.resources_required)
        for pre_vertex in self._pre_vertices:
            edge = SDRAMMachineEdge(
                pre_vertex, self._post_vertex, label="sdram")
            self._partition.add_edge(edge)
            pre_vertex.add_outgoing_sdram_partition(self._partition)
            chip_counter.add_core(pre_vertex.resources_required)

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self):
        return [self._post_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self):
        return [v.vertex_slice for v in self._pre_vertices]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(self, variable_to_record):
        return [self._post_vertex].extend(self._pre_vertices)

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self):
        pass

    @overrides(AbstractSplitterCommon.get_internal_sdram_partitions)
    def get_internal_sdram_partitions(self):
        return [self._partition]
