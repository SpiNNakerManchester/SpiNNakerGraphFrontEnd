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
from pacman.model.partitioner_splitters import SplitterSliceLegacy
from spinn_utilities.overrides import overrides


class BasicSDRAMSplitter(SplitterSliceLegacy):

    @overrides(SplitterSliceLegacy.get_out_going_vertices)
    def get_out_going_vertices(self, edge, outgoing_edge_partition):
        return self._get_map([SDRAMMachineEdge])

    @overrides(SplitterSliceLegacy.get_in_coming_vertices)
    def get_in_coming_vertices(
            self, edge, outgoing_edge_partition, src_machine_vertex):
        return self._get_map([SDRAMMachineEdge])
