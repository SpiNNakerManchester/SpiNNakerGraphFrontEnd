# Copyright (c) 2020 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from gfe_integration_tests.sdram_edge_tests.common import SdramTestVertex
from gfe_integration_tests.sdram_edge_tests.\
    test_multi_src_internal import SDRAMSplitter
from gfe_integration_tests.sdram_edge_tests import common
import spinnaker_graph_front_end as sim
from spinnaker_testbase import BaseTestCase


class TestMultiSrcSDRAMEdgeInsideOneAppVert(BaseTestCase):

    def setup(self):
        sim.setup(model_binary_module=common, time_scale_factor=5)
        vertex_1 = SdramTestVertex(12)
        vertex_1.splitter = SDRAMSplitter()
        sim.add_vertex_instance(vertex_1)
        sim.run(100)
        sim.stop()

    def test_local_verts_go_to_local_lpgs(self):
        self.runsafe(self.setup)
