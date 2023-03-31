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
Hello World program on SpiNNaker.

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""

import logging
import os
from spinn_utilities.config_holder import get_config_bool
from spinn_utilities.log import FormatAdapter
from spinn_front_end_common.data import FecDataView
import spinnaker_graph_front_end as front_end
from gfe_examples.hello_world_untimed.hello_world_vertex import (
    HelloWorldVertex)

logger = FormatAdapter(logging.getLogger(__name__))

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

# Put HelloWorldVertex onto 16 cores
total_number_of_cores = 16
prints_per_run = 10
runs = 2
for x in range(total_number_of_cores):
    front_end.add_machine_vertex_instance(
        HelloWorldVertex(label=f"Hello World {x}"))

for _ in range(runs):
    front_end.run_until_complete(prints_per_run)

if not get_config_bool("Machine", "virtual_board"):
    for placement in sorted(FecDataView.iterate_placemements(),
                            key=lambda p: (p.x, p.y, p.p)):

        if isinstance(placement.vertex, HelloWorldVertex):
            hello_world = placement.vertex.read()
            logger.info(
                "{}, {}, {} > {}",
                placement.x, placement.y, placement.p, hello_world)

front_end.stop()
