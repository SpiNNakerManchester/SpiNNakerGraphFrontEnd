"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""

import logging
import os
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.hello_world.hello_world_vertex import (
    HelloWorldVertex)

logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

# calculate total number of 'free' cores for the given board
# (i.e. does not include those busy with SARK or reinjection)
total_number_of_cores = \
    front_end.get_number_of_available_cores_on_machine()
total_number_of_cores = min(16, total_number_of_cores)

# fill all cores with a HelloWorldVertex each
for x in range(0, total_number_of_cores):
    front_end.add_machine_vertex_instance(
        HelloWorldVertex(label="Hello World at {}".format(x)))

front_end.run(10)

placements = front_end.placements()
buffer_manager = front_end.buffer_manager()

for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, HelloWorldVertex):
        hello_world = placement.vertex.read(placement, buffer_manager)
        logger.info("{}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, hello_world))

front_end.stop()
