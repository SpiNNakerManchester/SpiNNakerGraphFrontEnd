"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.

Author: Arthur Ceccotti
"""

import spynnaker_graph_front_end as front_end

from hello_world_vertex import HelloWorldVertex

import logging

import memory_reader
import os

logger = logging.getLogger(__name__)

front_end.setup(graph_label="hello_world",
                model_binary_module=file(os.getcwd() + "/../model_binaries/hello_world.aplx"))

dimenions = front_end.get_machine_dimensions()

machine_time_step = 100
time_scale_factor = 1

machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"

x_dimension = dimenions['x']+1
y_dimension = dimenions['y']+1
p_dimension = 18

# calculate total number of 'free' cores for the given board
# (ie. does not include those busy with sark or reinjection)
total_number_of_cores = (p_dimension-2) * x_dimension * y_dimension

# fill all cores with a HelloWorldVertex each
for x_position in range(0, total_number_of_cores):
        front_end.add_partitioned_vertex(
            HelloWorldVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="Hello World at x_position {}".format(x_position))

front_end.run(10)

for x in range(0, x_dimension):
    for y in range(0, y_dimension):
        for p in range(0, p_dimension):
            hello_world = memory_reader.read(transceiver=front_end.get_txrx(), x=x, y=y, p=p,
                                            recording_region = HelloWorldVertex.DATA_REGIONS.STRING_DATA.value)
            logger.info("{}, {}, {} > {}".format(x, y, p, hello_world))

front_end.stop()