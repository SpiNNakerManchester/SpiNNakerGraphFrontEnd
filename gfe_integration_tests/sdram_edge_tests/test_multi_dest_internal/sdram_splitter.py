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
from gfe_integration_tests.sdram_edge_tests.common import \
    SDRAMMachineVertex
from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import SDRAMMachineEdge
from pacman.model.graphs.machine.outgoing_edge_partitions import \
    SourceSegmentedSDRAMMachinePartition
from pacman.model.partitioner_interfaces import AbstractSplitterCommon
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
        super(SDRAMSplitter, self).__init__()
        self._partition_type = partition_type
        self._pre_vertex = None
        self._post_vertices = list()
        self._pre_slice = None
        self._post_slices = list()
        self._app_edge = None
        if self._partition_type == SourceSegmentedSDRAMMachinePartition:
            raise Exception("this splitter not for this")

    @overrides(AbstractSplitterCommon.get_pre_vertices)
    def get_pre_vertices(self, edge, outgoing_edge_partition):
        if edge == self._app_edge:
            return {}
        return {self._pre_vertex: [SDRAMMachineEdge]}

    @overrides(AbstractSplitterCommon.get_post_vertices)
    def get_post_vertices(self, edge, outgoing_edge_partition,
                          src_machine_vertex):
        if edge == self._app_edge:
            return {}
        return {self._post_vertex: [SDRAMMachineEdge]}

    @inject_items({"app_graph": "MemoryApplicationGraph"})
    @overrides(
        AbstractSplitterCommon.create_machine_vertices,
        additional_arguments=["app_graph"])
    def create_machine_vertices(
            self, resource_tracker, machine_graph, app_graph):
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
        resource_tracker.allocate_constrained_resources(
            self._pre_vertex.resources_required,
            self._governed_app_vertex.constraints,
            vertices=[self._pre_vertex])
        machine_graph.add_vertex(self._pre_vertex)

        for vertex_slice in self._post_slices:
            post_vertex = (
                SDRAMMachineVertex(
                    vertex_slice=vertex_slice, label=None,
                    constraints=None, app_vertex=self._governed_app_vertex,
                    sdram_cost=self._governed_app_vertex.fixed_sdram_value))
            self._post_vertices.append(post_vertex)

            # allocate res
            resource_tracker.allocate_constrained_resources(
                post_vertex.resources_required,
                self._governed_app_vertex.constraints,
                vertices=[post_vertex])

            # add to mac graph
            machine_graph.add_vertex(post_vertex)

        # add outgoing edge partition to mac graph
        machine_graph.add_outgoing_edge_partition(self._partition_type(
            identifier="sdram", pre_vertex=self._pre_vertex,
            label="sdram"))

        # add edge between the two verts app and mac
        self._app_edge = ApplicationEdge(
            self._governed_app_vertex, self._governed_app_vertex)
        app_graph.add_edge(self._app_edge, "sdram_app")

        # mac add
        for post_vertex in self._post_vertices:
            edge = SDRAMMachineEdge(
                self._pre_vertex, post_vertex, label="sdram",
                app_edge=self._app_edge)
            machine_graph.add_edge(edge, "sdram")

        return [self._pre_vertex].extend(self._post_vertices)

    @overrides(AbstractSplitterCommon.get_out_going_slices)
    def get_out_going_slices(self):
        return self._post_vertices, True

    @overrides(AbstractSplitterCommon.get_in_coming_slices)
    def get_in_coming_slices(self):
        return [self._pre_vertex], True

    @overrides(AbstractSplitterCommon.machine_vertices_for_recording)
    def machine_vertices_for_recording(self, variable_to_record):
        return [self._pre_vertex].extend(self._post_vertices)

    @overrides(AbstractSplitterCommon.reset_called)
    def reset_called(self):
        pass
