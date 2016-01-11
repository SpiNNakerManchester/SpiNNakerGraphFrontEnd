"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.

Author: Arthur Ceccotti
"""

import logging

import spynnaker_graph_front_end as front_end
from core_cluster_slave.cluster_slave_vertex import ClusterSlaveVertex
from core_root.root_vertex import RootVertex

import os

logger = logging.getLogger(__name__)

front_end.setup(graph_label="spiDB",
                model_binary_modules=[file(os.getcwd() + "/../model_binaries/root.aplx"),
                                      file(os.getcwd() + "/../model_binaries/cluster_slave.aplx")])

machine_time_step = 100
time_scale_factor = 1

machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"


#todo should not be hardcoded
x_dimension = 1
y_dimension = 1
p_dimension = 18

# calculate total number of 'free' cores for the given board
# (ie. does not include those busy with sark or reinjection)
# total_number_of_slaves = (p_dimension-2) * x_dimension * y_dimension

total_number_of_slaves = 16

vertices = list()

master_vertex = front_end.add_partitioned_vertex(
    RootVertex,
    {'label': 'Root',
     'machine_time_step': machine_time_step,
     'time_scale_factor': time_scale_factor,
     'port': machine_port},
    label="root")

for x_position in range(0, total_number_of_slaves-1):
        v = front_end.add_partitioned_vertex(
            ClusterSlaveVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="slave{}".format(x_position))
        vertices.append(v)

for c in range(0, 3):
    for x_position in range(0, total_number_of_slaves):
            v = front_end.add_partitioned_vertex(
                ClusterSlaveVertex,
                {'machine_time_step': machine_time_step,
                 'time_scale_factor': time_scale_factor},
                 label="slave{}".format(x_position))
            vertices.append(v)

front_end.run(5)
front_end.stop()