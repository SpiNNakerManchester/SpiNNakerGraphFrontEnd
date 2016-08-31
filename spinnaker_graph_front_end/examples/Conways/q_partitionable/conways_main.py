import spinnaker_graph_front_end as front_end


from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_application_edge import \
    ConwaysApplicationEdge
from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_application_cell import ConwaysApplicationGrid

runtime = 50
machine_time_step = 1000
time_scale_factor = 100
MAX_X_SIZE_OF_FABRIC = 7
MAX_Y_SIZE_OF_FABRIC = 7

# set up the front end and ask for the detected machines dimensions
front_end.setup(machine_time_step=machine_time_step,
                time_scale_factor=time_scale_factor)

# figure out if machine can handle simulation
cores = front_end.get_number_of_cores_on_machine()
if cores <= (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC):
    raise KeyError("Don't have enough cores to run simulation")

active_states = [(3, 2), (3, 3), (4, 3), (4, 4), (5, 2)]

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
