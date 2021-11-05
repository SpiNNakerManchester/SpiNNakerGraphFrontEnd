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
from gfe_integration_tests.sdram_edge_tests.common import (
    SDRAMMachineVertex)
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import (
    SDRAMMachineEdge, SourceSegmentedSDRAMMachinePartition)
from pacman.model.partitioner_splitters.abstract_splitters import (
    AbstractSplitterCommon)
from spinn_utilities.overrides import overrides


class SDRAMSplitter(AbstractSplitterCommon):
    """ sdram splitter
    """

    N_VERTS = 3

    __slots__ = [
        "_partition_type",
        "_pre_vertex",
        "_pre_slice",
        "_post_slices",
        "_post_vertices",
        "_app_edge"]

    def __init__(self, partition_type):
        super().__init__()
        self._partition_type = partition_type
        self._pre_vertex = None
        self._post_vertices = list()
        self._pre_slice = None
        self._post_slices = list()
        self._app_edge = None
        if self._partition_type == SourceSegmentedSDRAMMachinePartition:
            raise Exception("this splitter not for this")

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(self, outgoing_edge_partition):
        return [self._pre_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(self, outgoing_edge_partition):
        return [v.vertex_slice for v in self._post_vertices]

    def create_machine_vertices(self, plan_n_timesteps):
        # slices
        self._pre_slice = Slice(
            0, int(self._governed_app_vertex.n_atoms / self.N_VERTS))

        for count in range(1, self.N_VERTS):
            self._post_slices.append(Slice(
                self._pre_slice.n_atoms * count,
                self._pre_slice.n_atoms * count + self._pre_slice.n_atoms))

        # mac verts
        self._pre_vertex = (
            SDRAMMachineVertex(
                vertex_slice=self._pre_slice, label=None,
                constraints=None, app_vertex=self._governed_app_vertex,
                sdram_cost=self._governed_app_vertex.fixed_sdram_value))
        self._governed_app_vertex.remember_machine_vertex(self._pre_vertex)

        for vertex_slice in self._post_slices:
            post_vertex = (
                SDRAMMachineVertex(
                    vertex_slice=vertex_slice, label=None,
                    constraints=None, app_vertex=self._governed_app_vertex,
                    sdram_cost=self._governed_app_vertex.fixed_sdram_value))
            self._post_vertices.append(post_vertex)
            self._governed_app_vertex.remember_machine_vertex(post_vertex)

        return 1

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self):
        return self._post_vertices

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self):
        return [self._pre_vertex]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(self, variable_to_record):
        return [self._pre_vertex].extend(self._post_vertices)

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self):
        pass

    def get_internal_sdram_partitions(self):
        partition = self._partition_type(
            identifier="sdram", pre_vertex=self._pre_vertex,
            label="sdram")
        for post_vertex in self._post_vertices:
            edge = SDRAMMachineEdge(
                self._pre_vertex, post_vertex, label="sdram",
                app_edge=self._app_edge)
            partition.add_edge(edge)
        return [partition]
