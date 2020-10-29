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
from pacman.model.graphs.machine import SDRAMMachineEdge
from pacman.model.graphs.machine.outgoing_edge_partitions import \
    SourceSegmentedSDRAMMachinePartition
from pacman.model.partitioner_splitters import SplitterOneToOneLegacy
from spinn_utilities.overrides import overrides


class SDRAM_Splitter(SplitterOneToOneLegacy):
    """ sdram splitter
    """

    __slots__ = ["_partition_type"]

    def __init__(self, partition_type):
        super(SDRAM_Splitter, self).__init__()
        self._partition_type = partition_type
        if self._partition_type == SourceSegmentedSDRAMMachinePartition:
            raise Exception("this splitter not for this")

    @overrides(SplitterOneToOneLegacy.get_pre_vertices)
    def get_pre_vertices(self, edge, outgoing_edge_partition):
        return {self._machine_vertex: [SDRAMMachineEdge]}

    @overrides(SplitterOneToOneLegacy.get_post_vertices)
    def get_post_vertices(self, edge, outgoing_edge_partition,
                          src_machine_vertex):
        return {self._machine_vertex: [SDRAMMachineEdge]}

    @overrides(SplitterOneToOneLegacy.create_machine_vertices)
    def create_machine_vertices(self, resource_tracker, machine_graph):
        resource_tracker.allocate_constrained_resources(
            self._resources_required, self._governed_app_vertex.constraints,
            vertices=[self._machine_vertex])
        machine_graph.add_vertex(self._machine_vertex)
        machine_graph.add_outgoing_edge_partition(self._partition_type(
            identifier="sdram", pre_vertex=self._machine_vertex,
            label="sdram"))
        return self._machine_vertex
