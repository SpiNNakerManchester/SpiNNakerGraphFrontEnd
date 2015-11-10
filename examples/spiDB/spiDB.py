"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.

Author: Arthur Ceccotti
"""

import logging

import spynnaker_graph_front_end as front_end
from slave.slave_vertex import SlaveVertex
from master.master_vertex import MasterVertex
from boss.boss_vertex import BossVertex

from spiDB_socket_connection import SpiDBSocketConnection

import os

logger = logging.getLogger(__name__)

front_end.setup(graph_label="spiDB",
                model_binary_modules=[file(os.getcwd() + "/../model_binaries/slave.aplx"),
                                      file(os.getcwd() + "/../model_binaries/master.aplx")])

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
    BossVertex,
    {'label': 'Boss',
     'machine_time_step': machine_time_step,
     'time_scale_factor': time_scale_factor,
     'port': machine_port},
    label="Boss")

for x_position in range(0, total_number_of_slaves):
        v = front_end.add_partitioned_vertex(
            SlaveVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="Slave{}".format(x_position))
        vertices.append(v)


#TODO not from 0 to 3 hardcoded
#TODO LABELS
for c in range(0, 3):
    master_vertex = front_end.add_partitioned_vertex(
        MasterVertex,
        {'label': 'Master',
         'machine_time_step': machine_time_step,
         'time_scale_factor': time_scale_factor},
        label="Master{}".format(c))
    vertices.append(master_vertex)


    for x_position in range(0, total_number_of_slaves):
            v = front_end.add_partitioned_vertex(
                SlaveVertex,
                {'machine_time_step': machine_time_step,
                 'time_scale_factor': time_scale_factor},
                 label="Slave{}".format(x_position))
            vertices.append(v)

sst = SpiDBSocketConnection() #starts thread

front_end.run(10)
front_end.stop()