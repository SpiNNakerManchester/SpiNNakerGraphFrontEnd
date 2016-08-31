import spinnaker_graph_front_end as front_end


from spinnaker_graph_front_end.examples.Conways.r_partitionable.\
    conways_application_edge import \
    ConwaysApplicationEdge
from spinnaker_graph_front_end.examples.Conways.r_partitionable.\
    conways_application_cell import ConwaysApplicationGrid

runtime = 50
machine_time_step = 1000
time_scale_factor = 100
MAX_X_SIZE_OF_FABRIC = 28
MAX_Y_SIZE_OF_FABRIC = 28

# set up the front end and ask for the detected machines dimensions
front_end.setup(machine_time_step=machine_time_step,
                time_scale_factor=time_scale_factor)

# figure out if machine can handle simulation
cores = front_end.get_number_of_cores_on_machine()
if cores <= (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC):
    raise KeyError("Don't have enough cores to run simulation")

active_states = [
    (1, 1), (3, 1), (4, 2), (4, 3), (4, 4), (4, 5), (3, 5), (2, 5), (1, 4),  # bottom right
    (8, 3), (8, 4), (8, 5),  # line
    (17, 0), (17, 1), (16, 0), (16, 1), (15, 2), (15, 3), (14, 2), (14, 3),  # 2 squares
    (25, 2), (24, 2), (23, 2),  # virtual line left
    (25, 24), (24, 24), (23, 24), # virtual line right
    (11, 26), (11, 25), (10, 26), (9, 23), (8, 23), (8, 24),  # two triangles
    (1, 16), (1, 17), (2, 15), (2, 16), (2, 17), (2, 18), (3, 15), (3, 16),
    (3, 18), (3, 19), (4, 17), (4, 18),  # other glider

    (10, 9), (10, 10), (10, 11), (10, 15), (10, 16), (10, 17), (12, 7),
    (13, 7), (14, 7), (18, 7), (19, 7), (20, 7), (22, 9), (22, 10), (22, 11),
    (22, 15), (22, 16), (22, 17), (20, 19), (19, 19), (18, 19), (14, 19),
    (13, 19), (12, 19), (12, 14), (13, 14), (14, 14), (15, 15), (15, 16),
    (15, 17), (12, 12), (13, 12), (14, 12), (15, 11), (15, 10), (15, 9),
    (17, 9), (17, 10), (17, 11), (18, 12), (19, 12), (20, 12), (20, 14),
    (19, 14), (18, 14), (17, 15), (17, 16), (17, 17)]  # explosion

# build grid
grid = ConwaysApplicationGrid(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC,
                              active_states, "conway  fabric")
front_end.add_vertex_instance(grid)

# verify the initial state
output = ""
for y in range(MAX_X_SIZE_OF_FABRIC - 1, 0, -1):
    for x in range(0, MAX_Y_SIZE_OF_FABRIC):
        if grid.get_state_by_grid_coord(x, y):
            output += "X"
        else:
            output += " "
    output += "\n"
print output
print "\n\n"

# build the edge which represents the connection set for conways
front_end.add_application_edge_instance(
    ConwaysApplicationEdge(
        grid, grid, MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC), "STATE")

# run the simulation
front_end.run(runtime)

# get recorded data
recorded_data = None

# get the data per vertex
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):
        recorded_data = grid.get_data(
            front_end.buffer_manager(), front_end.machine_graph(),
            front_end.placements(), front_end.graph_mapper())

# visualise it in text form (bad but no vis this time)
for time in range(0, runtime):
    print "at time {}".format(time)
    output = ""
    for y in range(MAX_Y_SIZE_OF_FABRIC - 1, -1, -1):
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            if recorded_data[time][(x, y)]:
                output += "X"
            else:
                output += " "
        output += "\n"
    print output
    print "\n\n"

# clear the machine
front_end.stop()
