"""
heat demo main entrance allows users to run the game of life on the tool chain
"""


# spinn front end common imports
from spinn_front_end_common.utility_models.live_packet_gather import \
    LivePacketGather

# spinnman imports
from spinnman.messages.eieio.eieio_type import EIEIOType

# graph front end imports
import spynnaker_graph_front_end as front_end
from spynnaker_graph_front_end import MultiCastPartitionedEdge
from spynnaker_graph_front_end.utilities.connections.\
    live_event_connection import LiveEventConnection

# example imports
from examples.game_of_life.game_of_life_cell import GameOfLifeCell

# import the folder where all graph front end binaries are located
from examples import model_binaries

# method for dealing with heat element events
#def receive_events(label, time, neuron_ids):
#    pass



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

# hard code dimensions here (useful for debug) (chip based)
x_dimension = dimenions['x']
y_dimension = dimenions['y']

max_x_element_id = x_dimension * 4
max_y_element_id = y_dimension * 4

# overrwide dimensions
#max_x_element_id = 2
#max_y_element_id = 2

vertices = [None] * (x_dimension * 4)

live_gatherer = \
    front_end.add_partitioned_vertex(
        LivePacketGather,
        {'machine_time_step': machine_time_step,
         'timescale_factor': time_scale_factor,
         'label': "gatherer from heat elements",
         'ip_address': machine_host,
         'port': machine_recieve_port,
         'message_type': EIEIOType.KEY_PAYLOAD_32_BIT})

# build vertices

for x_position in range(0, max_x_element_id):
    for y_position in range(0, max_y_element_id):
        element = front_end.add_partitioned_vertex(
            GameOfLifeCell,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
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

        # check for the likely hood for a N link (incoming to south)
        if (x_position + 1) < max_x_element_id:
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position + 1][y_position]},
                label="North edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position + 1][y_position]),)
        elif toroid:
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[0][y_position]},
                label="North edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[0][y_position]),)

        # check for the likely hood for a NE link
        if ((x_position + 1) < max_x_element_id and
                (y_position + 1) < max_y_element_id):
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position + 1][y_position + 1]},
                label="North edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position + 1][y_position + 1]),)
        elif toroid:


        # check for the likely hood for a E link
        if (y_position + 1) < max_y_element_id:
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position][y_position + 1]},
                label="East edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position][y_position + 1]),)
        # check for the likely hood for a S link
        if (y_position - 1) >= 0:
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position][y_position - 1]},
                label="South edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position][y_position - 1]),)
        # check for the likely hood for a W link
        if (x_position - 1) >= 0:
            front_end.add_partitioned_edge(
                MultiCastPartitionedEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position - 1][y_position]},
                label="West edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position - 1][y_position]),)



# Set up the live connection for sending and receiving spikes
#live_spikes_connection = LiveEventConnection(
#    receive_labels=["pop_forward", "pop_backward"],
#    send_labels=["spike_injector_forward", "spike_injector_backward"])

# Set up callbacks to occur when spikes are received
#live_spikes_connection.add_receive_callback("gatherer from heat elements",
#                                            receive_events)

front_end.run(10)
front_end.stop()