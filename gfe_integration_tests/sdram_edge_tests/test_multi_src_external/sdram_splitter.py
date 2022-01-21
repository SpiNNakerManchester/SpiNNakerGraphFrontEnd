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
from collections import OrderedDict

from gfe_integration_tests.sdram_edge_tests.common import SDRAMMachineVertex
from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import SDRAMMachineEdge
from pacman.model.partitioner_splitters.abstract_splitters import (
    AbstractDependentSplitter)
from spinn_utilities.ordered_set import OrderedSet
from spinn_utilities.overrides import overrides


class SDRAMSplitter(AbstractDependentSplitter):
    """ sdram splitter
    """

    N_VERTS = 3

    __slots__ = [
        "_partition_type",
        "_pre_vertices",
        "_pre_slices",
        "_post_slice",
        "_post_vertex",
        "_app_edge"]

    def __init__(self, partition_type, other_splitter):
        super().__init__(other_splitter, "")
        self._partition_type = partition_type
        self._pre_vertices = OrderedSet()
        self._post_vertex = None
        self._pre_slices = OrderedSet()
        self._post_slice = None
        self._app_edge = None

    def _get_new_map(self, edge_types, vertices):
        """ builds map of machine vertex to edge type

        :param edge_types: the type of edges to add to the dict.

        :return: dict of vertex as key, edge types as list in value
        """
        result = OrderedDict()
        for vertex in vertices:
            result[vertex] = edge_types
        return result

    @overrides(AbstractDependentSplitter.get_out_going_vertices)
    def get_out_going_vertices(self, edge, outgoing_edge_partition):
        if edge == self._app_edge:
            return {}
        return self._get_new_map([SDRAMMachineEdge], self._pre_vertices)

    @overrides(AbstractDependentSplitter.get_in_coming_vertices)
    def get_in_coming_vertices(
            self, edge, outgoing_edge_partition, src_machine_vertex):
        if edge == self._app_edge:
            return {}
        return self._get_new_map([SDRAMMachineEdge], [self._post_vertex])

    @inject_items({"app_graph": "ApplicationGraph"})
    @overrides(
        AbstractDependentSplitter.create_machine_vertices,
        additional_arguments=["app_graph"])
    def create_machine_vertices(
            self, resource_tracker, machine_graph, app_graph):

        # slices
        self._post_slice = Slice(
            0, int(self._governed_app_vertex.n_atoms / self.N_VERTS))

        for count in range(1, self.N_VERTS):
            self._pre_slices.add(Slice(
                self._post_slice.n_atoms * count,
                self._post_slice.n_atoms * count + self._post_slice.n_atoms))

        # mac verts
        self._post_vertex = (
            SDRAMMachineVertex(
                vertex_slice=self._post_slice, label=None,
                constraints=None, app_vertex=self._governed_app_vertex,
                sdram_cost=self._governed_app_vertex.fixed_sdram_value))
        resource_tracker.allocate_constrained_resources(
            self._post_vertex.resources_required,
            self._governed_app_vertex.constraints)
        machine_graph.add_vertex(self._post_vertex)

        for vertex_slice in self._pre_slices:
            pre_vertex = (
                SDRAMMachineVertex(
                    vertex_slice=vertex_slice, label=None,
                    constraints=None, app_vertex=self._governed_app_vertex,
                    sdram_cost=self._governed_app_vertex.fixed_sdram_value))
            self._pre_vertices.add(pre_vertex)

            # allocate res
            resource_tracker.allocate_constrained_resources(
                pre_vertex.resources_required,
                self._governed_app_vertex.constraints)

            # add to mac graph
            machine_graph.add_vertex(pre_vertex)

        # add outgoing edge partition to mac graph
        if self._other_splitter is not None:
            total_pre_verts = list()
            total_pre_verts.extend(self._pre_vertices)
            for incoming_edge in app_graph.get_edges_ending_at_vertex(
                    self._governed_app_vertex):
                if (incoming_edge.pre_vertex.splitter ==
                        self._other_splitter):
                    outgoing_edge_partition = (
                        app_graph.get_outgoing_partition_for_edge(
                            incoming_edge))
                    total_pre_verts.extend(
                        self._other_splitter.get_out_going_vertices(
                            incoming_edge, outgoing_edge_partition))
            machine_graph.add_outgoing_edge_partition(self._partition_type(
                identifier="sdram", pre_vertices=total_pre_verts,
                label="sdram"))

        # add edge between the two verts app and mac
        self._app_edge = ApplicationEdge(
            self._governed_app_vertex, self._governed_app_vertex)
        app_graph.add_edge(self._app_edge, "sdram_app")

        # mac add
        for pre_vertex in self._pre_vertices:
            edge = SDRAMMachineEdge(
                pre_vertex, self._post_vertex, label="sdram",
                app_edge=self._app_edge)
            machine_graph.add_edge(edge, "sdram")

        return [self._post_vertex].extend(self._pre_vertices)

    @overrides(AbstractDependentSplitter.get_out_going_slices)
    def get_out_going_slices(self):
        return self._post_vertex, True

    @overrides(AbstractDependentSplitter.get_in_coming_slices)
    def get_in_coming_slices(self):
        return self._pre_vertices, True

    @overrides(AbstractDependentSplitter.machine_vertices_for_recording)
    def machine_vertices_for_recording(self, variable_to_record):
        return [self._post_vertex].extend(self._pre_vertices)

    @overrides(AbstractDependentSplitter.reset_called)
    def reset_called(self):
        pass
