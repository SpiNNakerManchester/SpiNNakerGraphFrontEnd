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
from gfe_integration_tests.simple_test_vertex import SimpleTestVertex
from gfe_integration_tests.sdram_edge_tests.common import (
    SDRAMSplitterExternal)
from pacman.model.graphs.application import ApplicationEdge
from gfe_integration_tests.sdram_edge_tests import common
import spinnaker_graph_front_end as sim
from pacman.model.graphs.machine import (
    DestinationSegmentedSDRAMMachinePartition)
from spinnaker_testbase import BaseTestCase


class TestMultiDestSDRAMEdgeBetweenTwoAppVerts(BaseTestCase):

    def setup(self):
        sim.setup(model_binary_module=common)
        vertex_1 = SimpleTestVertex(2, fixed_sdram_value=20)
        vertex_1.splitter = SDRAMSplitterExternal(
            DestinationSegmentedSDRAMMachinePartition)
        vertex_2 = SimpleTestVertex(2, fixed_sdram_value=20)
        vertex_2.splitter = SDRAMSplitterExternal(
            DestinationSegmentedSDRAMMachinePartition)
        vertex_3 = SimpleTestVertex(2, fixed_sdram_value=20)
        vertex_3.splitter = SDRAMSplitterExternal(
            DestinationSegmentedSDRAMMachinePartition)
        sim.add_vertex_instance(vertex_1)
        sim.add_vertex_instance(vertex_2)
        sim.add_vertex_instance(vertex_3)
        sim.add_application_edge_instance(
            ApplicationEdge(vertex_1, vertex_2), "sdram")
        sim.add_application_edge_instance(
            ApplicationEdge(vertex_1, vertex_3), "sdram")
        sim.run(100)
        sim.stop()

    def test_local_verts_go_to_local_lpgs(self):
        self.runsafe(self.setup)
