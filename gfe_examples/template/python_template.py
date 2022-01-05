# Copyright (c) 2017-2019 The University of Manchester
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

"""
Template for a Graph Front End program on SpiNNaker
"""

import logging
import os
import spinnaker_graph_front_end as front_end
from gfe_examples.template.template_vertex import TemplateVertex

logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=None, model_binary_folder=os.path.dirname(__file__))

# calculate total number of 'free' cores for the given board
# (i.e. does not include those busy with SARK or reinjection)
total_number_of_cores = \
    front_end.get_number_of_available_cores_on_machine()

# fill all cores with a Vertex each
for x in range(0, total_number_of_cores):
    front_end.add_machine_vertex(
        TemplateVertex,
        {},
        label="Template program at x {}".format(x))

# run for a specified length of time
front_end.run(10)

# set up placements (this is a simple example based on hello_world example
# that should be edited to suit the application)
for placement in sorted(front_end.placements(),
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, TemplateVertex):
        template_info = placement.vertex.read()
        logger.info("{}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, template_info))

front_end.stop()
