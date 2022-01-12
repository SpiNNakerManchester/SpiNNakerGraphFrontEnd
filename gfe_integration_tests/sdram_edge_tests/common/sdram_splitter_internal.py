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
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import (
    SDRAMMachineEdge, SourceSegmentedSDRAMMachinePartition)
from pacman.model.partitioner_splitters.abstract_splitters import (
    AbstractSplitterCommon)
from spinn_utilities.overrides import overrides
from gfe_integration_tests.sdram_edge_tests.common.\
    sdram_machine_vertex import SDRAMMachineVertex


class SDRAMSplitterInternal(AbstractSplitterCommon):
    """ sdram splitter
    """

    __slots__ = [
        "_partition_type",
        "_pre_vertex",
        "_pre_slice",
        "_post_slice",
        "_post_vertex",
        "_app_edge",
        "_sdram_part"]

    def __init__(self, partition_type):
        super().__init__()
        self._partition_type = partition_type
        self._pre_vertex = None
        self._post_vertex = None
        self._pre_slice = None
        self._post_slice = None
        self._app_edge = None
        self._sdram_part = None
        if self._partition_type == SourceSegmentedSDRAMMachinePartition:
            raise Exception("this splitter not for this")

    @overrides(AbstractSplitterCommon.get_out_going_vertices)
    def get_out_going_vertices(self, partition_id):
        return [self._pre_vertex]

    @overrides(AbstractSplitterCommon.get_in_coming_vertices)
    def get_in_coming_vertices(self, partition_id):
        return [self._post_vertex]

    def create_machine_vertices(self, chip_counter):
        # slices
        self._pre_slice = Slice(0, int(self._governed_app_vertex.n_atoms / 2))
        self._post_slice = Slice(
            int(self._governed_app_vertex.n_atoms / 2) + 1,
            int(self._governed_app_vertex.n_atoms - 1))

        # mac verts
        self._pre_vertex = (
            SDRAMMachineVertex(
                vertex_slice=self._pre_slice, label=None,
                constraints=None, app_vertex=self._governed_app_vertex,
                sdram_cost=self._governed_app_vertex.fixed_sdram_value))
        self._governed_app_vertex.remember_machine_vertex(self._pre_vertex)
        chip_counter.add_core(self._pre_vertex.resources_required)
        self._post_vertex = (
            SDRAMMachineVertex(
                vertex_slice=self._post_slice, label=None,
                constraints=None, app_vertex=self._governed_app_vertex,
                sdram_cost=self._governed_app_vertex.fixed_sdram_value))
        self._governed_app_vertex.remember_machine_vertex(self._post_vertex)
        chip_counter.add_core(self._pre_vertex.resources_required)

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self):
        return [self._post_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self):
        return [self._pre_vertex.vertex_slice]

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(self, variable_to_record):
        return [self._pre_vertex, self._post_vertex]

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self):
        pass

    @overrides(AbstractSplitterCommon.get_internal_sdram_partitions)
    def get_internal_sdram_partitions(self):
        sdram_part = self._partition_type(
            identifier="sdram", pre_vertex=self._pre_vertex,
            label="sdram")
        sdram_part.add_edge(SDRAMMachineEdge(
            self._pre_vertex, self._post_vertex, label="sdram"))
        return sdram_part
