"""
Template for a Graph Front End program on Spinnaker
"""

import logging
import os
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.template.template_vertex import (
    TemplateVertex)

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
placements = front_end.placements()
buffer_manager = front_end.buffer_manager()

for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, TemplateVertex):
        template_info = placement.vertex.read(placement, buffer_manager)
        logger.info("{}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, template_info))

front_end.stop()
