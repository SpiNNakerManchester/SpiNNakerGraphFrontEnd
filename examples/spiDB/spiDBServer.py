
import logging

import spynnaker_graph_front_end as front_end
from core_leaf.leaf_vertex import LeafVertex
from core_branch.branch_vertex import BranchVertex
from core_root.root_vertex import RootVertex

from tree_edge import TreeEdge

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

number_of_leaves = 13
number_of_branches = 3

root_vertex = front_end.add_partitioned_vertex(
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

for x_position in range(number_of_branches):
        v = front_end.add_partitioned_vertex(
            LeafVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="branch{}".format(x_position))

leaves = list()

for x_position in range(number_of_leaves):
        l = front_end.add_partitioned_vertex(
            LeafVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="leaf{}".format(x_position))
        leaves.append(l)

for x_position in range(3 * (number_of_leaves+number_of_branches+1)):
    l = front_end.add_partitioned_vertex(
        LeafVertex,
        {'machine_time_step': machine_time_step,
         'time_scale_factor': time_scale_factor},
         label="other_leaf{}".format(x_position))
    if x_position >= number_of_branches:
        leaves.append(l)

for l in leaves:
    front_end.add_partitioned_edge(
        TreeEdge,
        {'pre_subvertex': root_vertex,
         'post_subvertex': l},
        label="Edge from {} to {}"
              .format(root_vertex.label, l.label),
        partition_id="TREE_EDGE")

front_end.run(5)
front_end.stop()