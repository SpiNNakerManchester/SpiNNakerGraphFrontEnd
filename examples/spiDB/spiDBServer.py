
import logging

import spynnaker_graph_front_end as front_end
from core_leaf.leaf_vertex import LeafVertex
from core_branch.branch_vertex import BranchVertex
from core_root.root_vertex import RootVertex

import os

logger = logging.getLogger(__name__)

front_end.setup(graph_label="spiDB",
                model_binary_modules=[file(os.getcwd() + "/../model_binaries/root.aplx"),
                                      file(os.getcwd() + "/../model_binaries/leaf.aplx")])

machine_time_step = 100
time_scale_factor = 1

machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"

total_number_of_slaves = 16

vertices = list()

master_vertex = front_end.add_partitioned_vertex(
    RootVertex,
    {'label': 'Root',
     'machine_time_step': machine_time_step,
     'time_scale_factor': time_scale_factor,
     'port': machine_port},
    label="root")
"""
front_end.add_partitioned_vertex(
            BranchVertex,
            {'label':"branch{}".format(1),
             'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor})
"""
for x_position in range(total_number_of_slaves):
        v = front_end.add_partitioned_vertex(
            LeafVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="slave{}".format(x_position))
        vertices.append(v)

front_end.run(5)
front_end.stop()