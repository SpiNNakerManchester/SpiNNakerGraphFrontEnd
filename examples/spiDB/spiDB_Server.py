
# import main front end
import spinnaker_graph_front_end as front_end

# import binary location
from examples import model_binaries

# import db objects
from examples.spiDB.python.spiDB_graph_objects.leaf_vertex import LeafVertex
from examples.spiDB.python.spiDB_graph_objects.branch_vertex import BranchVertex
from examples.spiDB.python.spiDB_graph_objects.root_vertex import RootVertex
from examples.spiDB.python.spiDB_graph_objects.tree_edge import TreeEdge

# import server gui
from examples.spiDB.python.python_common import spiDB_Server_GUI
# import logging
import logging

logger = logging.getLogger(__name__)

n_chips_required = None
if front_end.is_allocated_machine():
    n_chips_required = 2

front_end.setup(graph_label="spiDB",
                model_binary_module=model_binaries,
                n_chips_required=n_chips_required)

# number of root cores
root_core = 1

# number of branches
first_branch = 2
n_branches = 3
first_leaf = 5
n_leaves = 10

machine_port = 11111
machine_receive_port = 22222
machine_host = "0.0.0.0"

chip_x_dimension = 2
chip_y_dimension = 2


roots = [[None for _ in range(chip_y_dimension)]
         for _ in range(chip_x_dimension)]
root_leaves = [[dict() for _ in range(chip_y_dimension)]
               for _ in range(chip_x_dimension)]

for x in range(chip_x_dimension):
    for y in range(chip_y_dimension):
        roots[x][y] = front_end.add_partitioned_vertex(
            RootVertex,
            {'label': 'root_{}_{}'.format(x,y),
             'port': machine_port if x is 0 and y is 0 else None,
             'placement': (x, y, 1)},
            label='root_{}_{}'.format(x, y))

for x in range(chip_x_dimension):
    for y in range(chip_y_dimension):
        for p in range(first_branch, first_branch+n_branches):
            b = front_end.add_partitioned_vertex(
                BranchVertex,
                {'label': 'branch_{}_{}_{}'.format(x, y, p),
                 'placement': (x, y, p)},
                label='branch_{}_{}_{}'.format(x, y, p))

for x in range(chip_x_dimension):
    for y in range(chip_y_dimension):
        for p in range(first_leaf, first_leaf+n_leaves):
            l = front_end.add_partitioned_vertex(
                LeafVertex,
                {'label': 'leaf_{}_{}_{}'.format(x, y, p),
                 'placement': (x, y, p)},
                label='leaf_{}_{}_{}'.format(x, y, p))
            root_leaves[x][y][p] = l

for x in range(chip_x_dimension):
    for y in range(chip_y_dimension):
        for p in range(first_leaf, first_leaf+n_leaves):
            front_end.add_partitioned_edge(
                TreeEdge,
                {'pre_subvertex': roots[x][y],
                 'post_subvertex': root_leaves[x][y][p]},
                label="edge_{}_to_{}"
                      .format(roots[x][y].label, root_leaves[x][y][p].label),
                partition_id="TREE_EDGE_{}".format(roots[x][y].label))

gui = spiDB_Server_GUI.GUIBuilder(front_end)

front_end.add_socket_address(
    database_ack_port_num=12098, database_notify_host="localhost",
    database_notify_port_num=12387)

front_end.run()
