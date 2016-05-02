
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
import math

logger = logging.getLogger(__name__)


def runner():
    """
    main method for the script.
    :return:
    """

    # allcoate machine (spalloc requirement)
    n_chips_required = None
    if front_end.is_allocated_machine():
        n_chips_required = 4

    # set up the backend
    front_end.setup(graph_label="spiDB",
                    model_binary_module=model_binaries,
                    n_chips_required=n_chips_required)

    # port the server on the machine listens to for commands
    machine_port = 11111

    # get the spinnaker machine and its dimensions
    machine = front_end.machine()
    machine_dimensions = front_end.get_machine_dimensions()
    chip_x_dimension = machine_dimensions['x']
    chip_y_dimension = machine_dimensions['y']

    # overload dimensions for easy debugging
    chip_x_dimension = 2
    chip_y_dimension = 2

    # build containers for the objects
    roots = [[None for _ in range(chip_y_dimension)]
             for _ in range(chip_x_dimension)]
    root_leaves = [[dict() for _ in range(chip_y_dimension)]
                   for _ in range(chip_x_dimension)]

    # add root nodes for every chip
    for x in range(chip_x_dimension):
        for y in range(chip_y_dimension):
            # add root node
            roots[x][y] = front_end.add_partitioned_vertex(
                RootVertex,
                {'label': 'root_{}_{}'.format(x,y),
                 'port': machine_port if x is 0 and y is 0 else None,
                 'placement': (x, y, 1)},
                label='root_{}_{}'.format(x, y))

            # locate none monitor cores and the number of sdp brnaches needed
            none_monitor_processors, num_branches = filter_cores(machine, x, y)

            # add branches
            for p in range(2, 2+num_branches):
                b = front_end.add_partitioned_vertex(
                    BranchVertex,
                    {'label': 'branch_{}_{}_{}'.format(x, y, p),
                     'placement': (x, y, p)},
                    label='branch_{}_{}_{}'.format(x, y, p))

            # add leaves
            for p in range(2+num_branches, none_monitor_processors - 1):
                # determine branch
                #####################################
                is_root_connected, branch = determine_brnach(p, num_branches)
                if is_root_connected:
                    branch_processor = 1
                else:
                    branch_processor = branch + 2

                l = front_end.add_partitioned_vertex(
                    LeafVertex,
                    {'label': 'leaf_{}_{}_{}'.format(x, y, p),
                     'branch_processor': branch_processor,
                     'placement': (x, y, p)},
                    label='leaf_{}_{}_{}'.format(x, y, p))
                root_leaves[x][y][p] = l

            # add edges from root to leaves
            for p in range(2+num_branches, none_monitor_processors - 1):
                front_end.add_partitioned_edge(
                    TreeEdge,
                    {'pre_subvertex': roots[x][y],
                     'post_subvertex': root_leaves[x][y][p]},
                    label="edge_{}_to_{}"
                          .format(roots[x][y].label,
                                  root_leaves[x][y][p].label),
                    partition_id="TREE_EDGE_{}".format(roots[x][y].label))

    # buidl the gui which will allow end users to kill the server after
    # doing work
    gui = spiDB_Server_GUI.GUIBuilder(front_end)

    # tied a clint based socket address for the system.
    front_end.add_socket_address(
        database_ack_port_num=12098, database_notify_host="localhost",
        database_notify_port_num=12387)

    # run the sevrer forever
    front_end.run()


def filter_cores(machine, x, y):
    """
    :param x: the chip x coord
    :param y: the chip y coord
    :param machine: the spinnaker machine
    :return: the number of nonemonitor cores, the number of branches needed
    """
    # deduce branches for sdp
    chip = machine.get_chip_at(x, y)
    none_monitor_processors = 0
    for processor in chip.processors:
        if not processor.is_monitor:
            none_monitor_processors += 1
    none_monitor_processors -= 1  # for root
    num_branches = 0
    if 18 >= none_monitor_processors >= 15:
        num_branches = 3
    elif 14 >= none_monitor_processors >= 10:
        num_branches = 2
    elif 9 >= none_monitor_processors >= 6:
        num_branches = 1
    elif 5 >= none_monitor_processors:
        num_branches = 0
    return none_monitor_processors, num_branches


def determine_brnach(leaf, num_branches):
    """
    dedueces if its a branch or a root comms.
    :param leaf: the leaf id
    :param num_branches: the number of brnaches avilable
    :return: bool is if a root or brnach and branch id if needed
    """
    if leaf == 0:
        return False, 0
    else:
        if num_branches * 4 < leaf:
            return True, None
        else:
            branch = leaf % num_branches
            return False, branch

if __name__ == "__main__":
    runner()

