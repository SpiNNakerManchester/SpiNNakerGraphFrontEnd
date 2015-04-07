"""
heat demo main entrance allows users to run the game of life on the tool chain

#TODO we need to add reinjector to make this work.
It drops packets like no tomorrow
"""


# spinn front end common imports
from spinn_front_end_common.utility_models.live_packet_gather import \
    LivePacketGather

# spinnman imports
from spinnman.messages.eieio.eieio_type import EIEIOType

# graph front end imports
import spynnaker_graph_front_end as front_end
from spynnaker_graph_front_end import MultiCastPartitionedEdge

# example imports
from examples.game_of_life.game_of_life_cell import GameOfLifeCell

# import the folder where all graph front end binaries are located
from examples import model_binaries

# set up the front end and ask for the detected machines dimensions
front_end.setup(graph_label="game_of_life_demo",
                model_binary_module=model_binaries)
dimenions = front_end.get_machine_dimensions()

machine_time_step = 1000
time_scale_factor = 1
machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"
toroid = True
record_on_sdram = True
runtime = 10

# hard code dimensions here (useful for debug) (chip based)
x_dimension = dimenions['x']
y_dimension = dimenions['y']

max_x_element_id = x_dimension * 4
max_y_element_id = y_dimension * 4

# overrwide dimensions
max_x_element_id = 7
max_y_element_id = 7

vertices = [None] * max_x_element_id

live_gatherer = \
    front_end.add_partitioned_vertex(
        LivePacketGather,
        {'machine_time_step': machine_time_step,
         'timescale_factor': time_scale_factor,
         'label': "gatherer from heat elements",
         'ip_address': machine_host,
         'port': machine_recieve_port})#,
         #'message_type': EIEIOType.KEY_PAYLOAD_32_BIT})

alive_cells = list()
# add a glider
if max_y_element_id > 5 and max_x_element_id > 5:
    alive_cells.extend([[2, 0], [2, 1], [2, 2], [1, 2], [0, 1]])

# build vertices
for x_position in range(0, max_x_element_id):
    for y_position in range(0, max_y_element_id):
        if [x_position, y_position] in alive_cells:
            element = front_end.add_partitioned_vertex(
                GameOfLifeCell,
                {'machine_time_step': machine_time_step,
                 'time_scale_factor': time_scale_factor,
                 'record_on_sdram': record_on_sdram,
                 'initial_state': GameOfLifeCell.STATES.ALIVE},
                label="game_of_life_cell at coords {}:{}"
                      .format(x_position, y_position))
        else:
            element = front_end.add_partitioned_vertex(
                GameOfLifeCell,
                {'machine_time_step': machine_time_step,
                 'time_scale_factor': time_scale_factor,
                 'record_on_sdram': record_on_sdram},
                label="game_of_life_cell at coords {}:{}"
                      .format(x_position, y_position))
        if vertices[x_position] is None:
            vertices[x_position] = list()
        vertices[x_position].append(element)

# build edges
for x_position in range(0, max_x_element_id):
    for y_position in range(0, max_y_element_id):

        # add a link from the heat element to the live packet gatherer
        front_end.add_partitioned_edge(
            MultiCastPartitionedEdge,
            {'pre_subvertex': vertices[x_position][y_position],
             'post_subvertex': live_gatherer},
            label="gatherer edge from vertex {} to live packet gatherer"
                  .format(vertices[x_position][y_position].label))

        if toroid:
            # do north
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[x_position % max_x_element_id]
                     [(y_position + 1) % max_y_element_id]},
                label="North edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position % max_x_element_id]
                                      [(y_position + 1) % max_y_element_id]),)

            # do ne
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[(x_position + 1) % max_x_element_id]
                             [(y_position + 1) % max_y_element_id]},
                label="North east edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[(x_position + 1) % max_x_element_id]
                                      [(y_position + 1) % max_y_element_id]))

            # do e
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[(x_position + 1) % max_x_element_id]
                             [y_position % max_y_element_id]},
                label="east edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[(x_position + 1) % max_x_element_id]
                                      [y_position % max_y_element_id]))

            # do se
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[(x_position + 1) % max_x_element_id]
                             [(y_position - 1) % max_y_element_id]},
                label="south east edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[(x_position + 1) % max_x_element_id]
                                      [(y_position - 1) % max_y_element_id]))

            # do south
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[x_position % max_x_element_id]
                             [(y_position - 1) % max_y_element_id]},
                label="south edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position % max_x_element_id]
                                      [(y_position - 1) % max_y_element_id]))

            # do south west
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[(x_position - 1) % max_x_element_id]
                             [(y_position - 1) % max_y_element_id]},
                label="south west edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[(x_position - 1) % max_x_element_id]
                                      [(y_position - 1) % max_y_element_id]))

            # do west
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[(x_position - 1) % max_x_element_id]
                             [y_position % max_y_element_id]},
                label="west edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[(x_position - 1) % max_x_element_id]
                                      [y_position % max_y_element_id]),)

            # do north west
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex':
                     vertices[(x_position - 1) % max_x_element_id]
                             [(y_position + 1) % max_y_element_id]},
                label="North west edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[(x_position - 1) % max_x_element_id]
                                      [(y_position + 1) % max_y_element_id]),)

        else:  # not a torioid, need to be a bit careful
            # check for the likely hood for a N link (incoming to south)
            if (y_position + 1) < max_y_element_id:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position][y_position + 1]},
                    label="North edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position][y_position + 1]),)

            # check for the likely hood for a NE link
            if ((x_position + 1) < max_x_element_id and
                    (y_position + 1) < max_y_element_id):
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position + 1][y_position + 1]},
                    label="North east edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position + 1][y_position + 1]),)

            # check for the likely hood for a E link
            if (x_position + 1) < max_x_element_id:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position + 1][y_position]},
                    label="East edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position + 1][y_position]),)

            # check for the south east link
            if (y_position - 1) < max_y_element_id and (x_position + 1) >= 0:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position + 1][y_position - 1]},
                    label="south east edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position + 1][y_position - 1]),)

            # check for the likely hood for a S link
            if (y_position - 1) >= 0:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position][y_position - 1]},
                    label="South edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position][y_position - 1]),)

            # check for the likely hood for a south west link
            if (y_position - 1) >= 0 and (x_position - 1) >= 0:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position - 1][y_position - 1]},
                    label="South west edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position - 1][y_position - 1]),)

            # check for the likely hood for a W link
            if (x_position - 1) >= 0:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position - 1][y_position]},
                    label="West edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position - 1][y_position]),)

            # check for the likely hood for a north west link
            if (x_position - 1) >= 0 and (y_position + 1) < max_y_element_id:
                front_end.add_partitioned_edge(
                    MultiCastPartitionedEdge,
                    {'pre_subvertex': vertices[x_position][y_position],
                     'post_subvertex': vertices[x_position - 1][y_position + 1]},
                    label="West edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position - 1][y_position + 1]),)

# run the simulation for 10 seconds
front_end.run(runtime)

# extract states from sdram
if record_on_sdram:
    states = [None] * max_x_element_id
    trasnciever = front_end.get_transciever()
    for x_position in range(0, max_x_element_id):
        for y_position in range(0, max_y_element_id):
            placement = \
                front_end.get_placement(vertices[x_position][y_position])
            print "extracting data for cell on core {}:{}:{}".format(
                placement.x, placement.y, placement.p
            )
            if states[x_position] is None:
                states[x_position] = list()
            states[x_position].append(
                vertices[x_position][y_position].
                get_recorded_states(trasnciever, placement))

    print states
    for time_step in range(runtime):
        for x_position in range(0, max_x_element_id):
            line = ""
            for y_position in range(0, max_y_element_id):
                state = states[x_position][y_position][time_step]
                if state == 0:
                    line += "O"
                else:
                    line += "X"
            print line
        print "\n\n"


# stop the simulation
front_end.stop()