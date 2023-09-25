# Copyright (c) 2017 The University of Manchester
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

"""
Hello World program on SpiNNaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""

import os
from spinnaker_testbase import BaseTestCase
import spinnaker_graph_front_end as front_end
from gfe_examples.hello_world.hello_world_vertex import HelloWorldVertex


class TestHelloWorld(BaseTestCase):

    # NO unittest_setup() as sim.setup is called

    def test_hello_world(self):
        front_end.setup(
            n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

        # Put HelloWorldVertex onto 16 cores
        total_number_of_cores = 16
        for x in range(total_number_of_cores):
            front_end.add_machine_vertex_instance(
                HelloWorldVertex(n_hellos=10, label=f"Hello World at {x}"))

        front_end.run(10)
        front_end.run(10)

        front_end.stop()
