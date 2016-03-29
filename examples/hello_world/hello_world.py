"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""

import spinnaker_graph_front_end as front_end

from hello_world_vertex import HelloWorldVertex

# import the folder where all graph front end binaries are located
from examples import model_binaries

import logging

logger = logging.getLogger(__name__)

front_end.setup(graph_label="hello_world",
                model_binary_module=model_binaries)

dimensions = front_end.get_machine_dimensions()

machine_time_step = 1000
time_scale_factor = 1

x_dimension = dimensions['x'] + 1
y_dimension = dimensions['y'] + 1

x_dimension = 2
y_dimension = 2

p_dimension = 16

# calculate total number of 'free' cores for the given board
# (i.e. does not include those busy with SARK or reinjection)
total_number_of_cores = (p_dimension - 2) * x_dimension * y_dimension

# fill all cores with a HelloWorldVertex each
for x_position in range(0, total_number_of_cores):
        front_end.add_partitioned_vertex(
            HelloWorldVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
            label="Hello World at x_position {}".format(x_position))

front_end.run(10)

placements = front_end.placements()
buffer_manager = front_end.buffer_manager()
# read out sdram
for x in range(0, x_dimension):
    for y in range(0, y_dimension):
        for p in range(0, p_dimension):
            if placements.is_subvertex_on_processor(x, y, p):
                vertex = placements.get_subvertex_on_processor(x, y, p)
                hello_world = vertex.read(
                    placement=placements.get_placement_of_subvertex(vertex),
                    buffer_manager=buffer_manager)
                logger.info("{}, {}, {} > {}".format(x, y, p, hello_world))

front_end.stop()
