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
import unittest

from fec_integration_tests.interface.interface_functions.\
    simple_test_vertex import SimpleTestVertex
from gfe_integration_tests.sdram_edge_tests.\
    test_multi_src_internal import SDRAMSplitter
from pacman.model.graphs.machine.outgoing_edge_partitions import (
    SourceSegmentedSDRAMMachinePartition)
from gfe_integration_tests.sdram_edge_tests import common
import spinnaker_graph_front_end as sim


class TestMultiSrcSDRAMEdgeInsideOneAppVert(unittest.TestCase):

    def setup(self):
        sim.setup(model_binary_module=common)
        vertex_1 = SimpleTestVertex(12, fixed_sdram_value=20)
        vertex_1.splitter = SDRAMSplitter(
            SourceSegmentedSDRAMMachinePartition)
        sim.add_vertex_instance(vertex_1)
        sim.run(100)
        sim.stop()

    def test_local_verts_go_to_local_lpgs(self):
        self.setup()
