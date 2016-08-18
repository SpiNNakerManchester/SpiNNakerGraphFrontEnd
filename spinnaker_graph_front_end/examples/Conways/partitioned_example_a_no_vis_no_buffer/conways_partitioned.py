
import spinnaker_graph_front_end as front_end
import sys

from spinnaker_graph_front_end.examples.Conways.\
    partitioned_example_a_no_vis_no_buffer.conways_basic_cell \
    import ConwayBasicCell
from pacman.model.graphs.machine.impl.machine_edge import MachineEdge

n_chips_required = 48
runtime = 50
machine_time_step = 100
time_scale_factor = 2
MAX_X_SIZE_OF_FABRIC = 7
MAX_Y_SIZE_OF_FABRIC = 7

# set up the front end and ask for the detected machines dimensions
front_end.setup(
    graph_label="conway_graph", model_binary_module=sys.modules[__name__],
    n_chips_required=n_chips_required)

# figure out if machine can handle simulation
cores = front_end.get_number_of_cores_on_machine()
if cores <= (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC):
    raise KeyError("Dont have enough cores to run simulation")

# contain the verts for the connection aspect
vertices = [
    [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
    for _ in range(MAX_Y_SIZE_OF_FABRIC)]

active_states = [(2,2), (3, 2), (3, 3), (4, 3), (2, 4)]

# build verts
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):
        vert = ConwayBasicCell(
            "cell{}".format((x * MAX_X_SIZE_OF_FABRIC) + y),
            (x, y) in active_states)
        vertices[x][y] = vert
        front_end.add_machine_vertex_instance(vert)

# verify the initial state
output = ""
for y in range(MAX_X_SIZE_OF_FABRIC - 1, 0, -1):
    for x in range(0, MAX_Y_SIZE_OF_FABRIC):
        if vertices[x][y].state:
            output += "X"
        else:
            output += " "
    output += "\n"
print output
print "\n\n"

# build edges
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):

        positions = [
            (x, (y + 1) % MAX_Y_SIZE_OF_FABRIC, "N"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
                (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NE"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC, y, "E"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
                (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SE"),
            (x, (y - 1) % MAX_Y_SIZE_OF_FABRIC, "S"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
                (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SW"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC, y, "W"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
                (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NW")]

        for (dest_x, dest_y, compass) in positions:
            front_end.add_machine_edge_instance(
                MachineEdge(
                    vertices[x][y], vertices[dest_x][dest_y],
                    label=compass), "STATE")

# run the simulation
front_end.run(runtime)

# get recorded data
recorded_data = dict()

# get the data per vertex
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):
        recorded_data[(x, y)] = vertices[x][y].get_data(
            front_end.transceiver(),
            front_end.placements().get_placement_of_vertex(vertices[x][y]))

# visualise it in text form (bad but no vis this time)
for time in range(0, runtime):
    print "at time {}".format(time)
    output = ""
    for y in range(MAX_X_SIZE_OF_FABRIC - 1, 0, -1):
        for x in range(0, MAX_Y_SIZE_OF_FABRIC):
            if recorded_data[(x, y)][time]:
                output += "X"
            else:
                output += " "
        output += "\n"
    print output
    print "\n\n"

# clear the machine
front_end.stop()
