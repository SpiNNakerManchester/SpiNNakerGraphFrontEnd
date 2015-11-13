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
from core_cluster_head.cluster_head_vertex import ClusterHeadVertex
from core_root.root_vertex import RootVertex

from spiDB_socket_connection import SpiDBSocketConnection

import os

logger = logging.getLogger(__name__)

front_end.setup(graph_label="spiDB",
                model_binary_modules=[file(os.getcwd() + "/../model_binaries/root.aplx"),
                                      file(os.getcwd() + "/../model_binaries/cluster_head.aplx"),
                                      file(os.getcwd() + "/../model_binaries/cluster_slave.aplx")])

#dimenions = front_end.get_machine_dimensions() #todo with the new changes this gets broken

machine_time_step = 100
time_scale_factor = 1

machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"

#x_dimension = dimenions['x']+1
#y_dimension = dimenions['y']+1

x_dimension = 1
y_dimension = 1
p_dimension = 18

# calculate total number of 'free' cores for the given board
# (ie. does not include those busy with sark or reinjection)

#total_number_of_slaves = (p_dimension-2) * x_dimension * y_dimension

total_number_of_slaves = 15

vertices = list()

master_vertex = front_end.add_partitioned_vertex(
    RootVertex,
    {'label': 'Boss',
     'machine_time_step': machine_time_step,
     'time_scale_factor': time_scale_factor,
     'port': machine_port},
    label="root")

for x_position in range(0, total_number_of_slaves):
        v = front_end.add_partitioned_vertex(
            ClusterSlaveVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="slave{}".format(x_position))
        vertices.append(v)


#TODO not from 0 to 3 hardcoded
#TODO LABELS
for c in range(0, 3):
    master_vertex = front_end.add_partitioned_vertex(
        ClusterHeadVertex,
        {'label': 'Master',
         'machine_time_step': machine_time_step,
         'time_scale_factor': time_scale_factor},
        label="head{}".format(c))
    vertices.append(master_vertex)


    for x_position in range(0, total_number_of_slaves):
            v = front_end.add_partitioned_vertex(
                ClusterSlaveVertex,
                {'machine_time_step': machine_time_step,
                 'time_scale_factor': time_scale_factor},
                 label="slave{}".format(x_position))
            vertices.append(v)

sst = SpiDBSocketConnection() #starts thread

front_end.run(10)
front_end.stop()