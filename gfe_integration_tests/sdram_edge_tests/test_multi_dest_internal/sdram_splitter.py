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
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import (
    SDRAMMachineEdge, DestinationSegmentedSDRAMMachinePartition)
from pacman.model.partitioner_splitters.abstract_splitters import (
    AbstractSplitterCommon)
from spinn_utilities.overrides import overrides
from spinn_front_end_common.data import FecDataView


class SDRAMSplitter(AbstractSplitterCommon):
    """ sdram splitter
    """

    N_VERTS = 3

    __slots__ = [
        "_pre_vertex",
        "_pre_slice",
        "_post_slices",
        "_post_vertices",
        "_partition"]

    def __init__(self):
        super().__init__()
        self._pre_vertex = None
        self._post_vertices = list()
        self._pre_slice = None
        self._post_slices = list()

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(self, partition_id):
        return self._post_vertices

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(self, partition_id):
        return [self._pre_vertex]

    def create_machine_vertices(self, chip_counter):
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
                sdram_cost=20))
        self._governed_app_vertex.remember_machine_vertex(self._pre_vertex)

        for vertex_slice in self._post_slices:
            post_vertex = (
                SDRAMMachineVertex(
                    vertex_slice=vertex_slice, label=None,
                    constraints=None, app_vertex=self._governed_app_vertex))
            self._post_vertices.append(post_vertex)
            self._governed_app_vertex.remember_machine_vertex(post_vertex)

        self._partition = DestinationSegmentedSDRAMMachinePartition(
            identifier="sdram", pre_vertex=self._pre_vertex)
        self._pre_vertex.add_outgoing_sdram_partition(self._partition)
        for post_vertex in self._post_vertices:
            edge = SDRAMMachineEdge(
                self._pre_vertex, post_vertex, label="sdram")
            self._partition.add_edge(edge)
            post_vertex.add_incoming_sdram_partition(self._partition)
            chip_counter.add_core(post_vertex.resources_required)

        chip_counter.add_core(self._pre_vertex.resources_required)
        return 1

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self):
        return [v.vertex_slice for v in self._post_vertices]

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self):
        return [self._pre_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(self, variable_to_record):
        return [self._pre_vertex].extend(self._post_vertices)

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self):
        pass

    def get_internal_sdram_partitions(self):
        return [self._partition]
