import spinnaker_graph_front_end as front_end

from pacman.model.constraints.placer_constraints.\
    placer_chip_and_core_constraint import \
    PlacerChipAndCoreConstraint
from spinnaker_graph_front_end.examples.Conways.\
    partitioned_example_c_vis_buffer.conways_basic_cell \
    import ConwayBasicCell
from pacman.model.graphs.machine.impl.machine_edge import MachineEdge

runtime = 500
machine_time_step = 1000
time_scale_factor = 1000
MAX_X_SIZE_OF_FABRIC = 7
MAX_Y_SIZE_OF_FABRIC = 7

# set up the front end and ask for the detected machines dimensions
front_end.setup(time_scale_factor=time_scale_factor)

# figure out if machine can handle simulation
cores = front_end.get_number_of_cores_on_machine()
if cores <= (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC):
    raise KeyError("Don't have enough cores to run simulation")

# contain the vertices for the connection aspect
vertices = [
    [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
    for _ in range(MAX_Y_SIZE_OF_FABRIC)]

active_states = [(2, 2), (3, 2), (3, 3), (4, 3), (2, 4)]

placement_to_make_tubogrid_work_correctly = dict()
placement_to_make_tubogrid_work_correctly[(6, 6)] = (0, 0, 1)
placement_to_make_tubogrid_work_correctly[(6, 5)] = (0, 0, 2)
placement_to_make_tubogrid_work_correctly[(6, 4)] = (0, 0, 3)
placement_to_make_tubogrid_work_correctly[(6, 3)] = (0, 0, 4)
placement_to_make_tubogrid_work_correctly[(6, 2)] = (1, 0, 1)
placement_to_make_tubogrid_work_correctly[(6, 1)] = (1, 0, 2)
placement_to_make_tubogrid_work_correctly[(6, 0)] = (1, 0, 3)

placement_to_make_tubogrid_work_correctly[(5, 6)] = (0, 0, 5)
placement_to_make_tubogrid_work_correctly[(5, 5)] = (0, 0, 6)
placement_to_make_tubogrid_work_correctly[(5, 4)] = (0, 0, 7)
placement_to_make_tubogrid_work_correctly[(5, 3)] = (0, 0, 8)
placement_to_make_tubogrid_work_correctly[(5, 2)] = (1, 0, 5)
placement_to_make_tubogrid_work_correctly[(5, 1)] = (1, 0, 6)
placement_to_make_tubogrid_work_correctly[(5, 0)] = (1, 0, 7)

placement_to_make_tubogrid_work_correctly[(4, 6)] = (0, 0, 9)
placement_to_make_tubogrid_work_correctly[(4, 5)] = (0, 0, 10)
placement_to_make_tubogrid_work_correctly[(4, 4)] = (0, 0, 11)
placement_to_make_tubogrid_work_correctly[(4, 3)] = (0, 0, 12)
placement_to_make_tubogrid_work_correctly[(4, 2)] = (1, 0, 9)
placement_to_make_tubogrid_work_correctly[(4, 1)] = (1, 0, 10)
placement_to_make_tubogrid_work_correctly[(4, 0)] = (1, 0, 11)

placement_to_make_tubogrid_work_correctly[(3, 6)] = (0, 0, 13)
placement_to_make_tubogrid_work_correctly[(3, 5)] = (0, 0, 14)
placement_to_make_tubogrid_work_correctly[(3, 4)] = (0, 0, 15)
placement_to_make_tubogrid_work_correctly[(3, 3)] = (0, 0, 16)
placement_to_make_tubogrid_work_correctly[(3, 2)] = (1, 0, 13)
placement_to_make_tubogrid_work_correctly[(3, 1)] = (1, 0, 14)
placement_to_make_tubogrid_work_correctly[(3, 0)] = (1, 0, 15)

placement_to_make_tubogrid_work_correctly[(2, 6)] = (0, 1, 1)
placement_to_make_tubogrid_work_correctly[(2, 5)] = (0, 1, 2)
placement_to_make_tubogrid_work_correctly[(2, 4)] = (0, 1, 3)
placement_to_make_tubogrid_work_correctly[(2, 3)] = (0, 1, 4)
placement_to_make_tubogrid_work_correctly[(2, 2)] = (1, 1, 1)
placement_to_make_tubogrid_work_correctly[(2, 1)] = (1, 1, 2)
placement_to_make_tubogrid_work_correctly[(2, 0)] = (1, 1, 3)

placement_to_make_tubogrid_work_correctly[(1, 6)] = (0, 1, 5)
placement_to_make_tubogrid_work_correctly[(1, 5)] = (0, 1, 6)
placement_to_make_tubogrid_work_correctly[(1, 4)] = (0, 1, 7)
placement_to_make_tubogrid_work_correctly[(1, 3)] = (0, 1, 8)
placement_to_make_tubogrid_work_correctly[(1, 2)] = (1, 1, 5)
placement_to_make_tubogrid_work_correctly[(1, 1)] = (1, 1, 6)
placement_to_make_tubogrid_work_correctly[(1, 0)] = (1, 1, 7)

placement_to_make_tubogrid_work_correctly[(0, 6)] = (0, 1, 9)
placement_to_make_tubogrid_work_correctly[(0, 5)] = (0, 1, 10)
placement_to_make_tubogrid_work_correctly[(0, 4)] = (0, 1, 11)
placement_to_make_tubogrid_work_correctly[(0, 3)] = (0, 1, 12)
placement_to_make_tubogrid_work_correctly[(0, 2)] = (1, 1, 9)
placement_to_make_tubogrid_work_correctly[(0, 1)] = (1, 1, 10)
placement_to_make_tubogrid_work_correctly[(0, 0)] = (1, 1, 11)

# build vertices
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):
        vert = ConwayBasicCell(
            "cell{}".format((x * MAX_X_SIZE_OF_FABRIC) + y),
            (x, y) in active_states)
        vert.add_constraint(PlacerChipAndCoreConstraint(
            placement_to_make_tubogrid_work_correctly[(x, y)][0],
            placement_to_make_tubogrid_work_correctly[(x, y)][1],
            placement_to_make_tubogrid_work_correctly[(x, y)][2]))
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
                    vertices[x][y], vertices[dest_x][dest_y], label=compass),
                "STATE")

# set up vis
# inputs = [
#    "/home/alan/spinnaker/alpha_package_103_git/spinnaker_tools/"
#    "tools/tubogrid"
# ]
# child = subprocess.Popen(
#    inputs, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
#    stdin=subprocess.PIPE)

# run the simulation
front_end.run(runtime)

# get recorded data
recorded_data = dict()

# get the data per vertex
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):
        recorded_data[(x, y)] = vertices[x][y].get_data(
            front_end.buffer_manager(),
            front_end.placements().get_placement_of_subvertex(vertices[x][y]))

# visualise it in text form (bad but no vis this time)
for time in range(0, runtime):
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

# wait till vis is stopped
# child.wait()
