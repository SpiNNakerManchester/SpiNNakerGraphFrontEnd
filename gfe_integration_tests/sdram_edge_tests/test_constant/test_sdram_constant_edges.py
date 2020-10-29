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
import os
import unittest

from fec_integration_tests.interface.interface_functions.\
    simple_test_vertex import SimpleTestVertex
from gfe_integration_tests.sdram_edge_tests.test_constant import SDRAM_Splitter
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.machine.outgoing_edge_partitions import (
    ConstantSDRAMMachinePartition)
from gfe_integration_tests.sdram_edge_tests import test_constant
import spinnaker_graph_front_end as sim

class TestLPGPreAllocateRes(unittest.TestCase):

    def setup(self):
        sim.setup(model_binary_module=test_constant)
        vertex_1 = SimpleTestVertex(2, fixed_sdram_value=20)
        vertex_1.splitter = SDRAM_Splitter(ConstantSDRAMMachinePartition)
        vertex_2 = SimpleTestVertex(2, fixed_sdram_value=20)
        vertex_2.splitter = SDRAM_Splitter(ConstantSDRAMMachinePartition)
        sim.add_vertex_instance(vertex_1)
        sim.add_vertex_instance(vertex_2)
        sim.add_application_edge_instance(
            ApplicationEdge(vertex_1, vertex_2), "sdram")
        sim.run(100)

    def test_local_verts_go_to_local_lpgs(self):
        self.setup()
