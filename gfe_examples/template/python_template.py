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
Template for a Graph Front End program on SpiNNaker
"""

import logging
import os
from spinn_utilities.log import FormatAdapter
from spinn_front_end_common.data import FecDataView
import spinnaker_graph_front_end as front_end
from gfe_examples.template.template_vertex import TemplateVertex

logger = FormatAdapter(logging.getLogger(__name__))

# Set n_chips_required to enough to get three boards
# Note this value is only used if spalloc_server or remote_spinnaker_url
# are set in the cfg.
# Otherwise the machine specified is used even if smaller
n_chips_required = 49

front_end.setup(
    n_chips_required=n_chips_required,
    model_binary_folder=os.path.dirname(__file__))

# calculate total number of 'free' cores for the given board
# (i.e. does not include those busy with SARK or reinjection)
total_number_of_cores = front_end.get_number_of_available_cores_on_machine()

# fill all cores with a Vertex each
for x in range(0, total_number_of_cores):
    front_end.add_machine_vertex_instance(
        TemplateVertex(label=f"Template program at x {x}"))

# run for a specified length of time
front_end.run(10)

# set up placements (this is a simple example based on hello_world example
# that should be edited to suit the application)
for placement in sorted(FecDataView.iterate_placemements(),
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, TemplateVertex):
        template_info = placement.vertex.read()
        logger.info("{}, {}, {} > {}", placement.x, placement.y,
                    placement.p, template_info)

front_end.stop()
