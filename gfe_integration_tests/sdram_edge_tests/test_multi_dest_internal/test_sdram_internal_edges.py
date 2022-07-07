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
from gfe_integration_tests.sdram_edge_tests.common import SdramTestVertex
from gfe_integration_tests.sdram_edge_tests.test_multi_dest_internal import (
    SDRAMSplitter)
from gfe_integration_tests.sdram_edge_tests import common
import spinnaker_graph_front_end as sim
from spinnaker_testbase import BaseTestCase


class TestMultiDestSDRAMEdgeInsideOneAppVert(BaseTestCase):

    def setup(self):
        sim.setup(model_binary_module=common)
        vertex_1 = SdramTestVertex(12)
        vertex_1.splitter = SDRAMSplitter()
        sim.add_vertex_instance(vertex_1)
        sim.run(100)
        sim.stop()

    def test_multi_dest(self):
        self.runsafe(self.setup)
