"""
heat demo main entrance allows users to run the heat demo on the tool chain
"""


# spinn front end common imports
from spinn_front_end_common.utility_models.live_packet_gather import \
    LivePacketGather

# SpiNNMan imports
from spinnman.messages.eieio.eieio_type import EIEIOType

# graph front end imports
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end import ReverseIpTagMultiCastSource
from spinnaker_graph_front_end import MultiCastPartitionedEdge

# example imports
from examples.heat_demo.heat_demo_command_edge import HeatDemoCommandEdge
from examples.heat_demo.heat_demo_vertex import HeatDemoVertexPartitioned
from examples.heat_demo.heat_demo_edge import HeatDemoEdge

# import the folder where all graph front end binaries are located
from examples import model_binaries

# method for dealing with heat element events
# def receive_events(label, time, neuron_ids):
#     pass

# set up the front end and ask for the detected machines dimensions
front_end.setup(graph_label="heat_demo_graph",
                model_binary_module=model_binaries)
dimensions = front_end.get_machine_dimensions()

machine_time_step = 1000
time_scale_factor = 1
machine_port = 11111
machine_receive_port = 22222
machine_host = "0.0.0.0"

# hard code dimensions here (useful for debug) (chip based)
x_dimension = dimensions['x']
y_dimension = dimensions['y']

max_x_element_id = x_dimension * 4
max_y_element_id = y_dimension * 4

# override dimensions
max_x_element_id = 2
max_y_element_id = 2

vertices = [None] * (x_dimension * 4)


command_injector = \
    front_end.add_partitioned_vertex(
        ReverseIpTagMultiCastSource,
        {'n_neurons': 1, 'machine_time_step': machine_time_step,
         'timescale_factor': time_scale_factor, 'label': "injector_from_vis",
         'port': machine_port})

live_gatherer = \
    front_end.add_partitioned_vertex(
        LivePacketGather,
        {'machine_time_step': machine_time_step,
         'timescale_factor': time_scale_factor,
         'label': "gatherer from heat elements",
         'ip_address': machine_host,
         'port': machine_receive_port,
         'message_type': EIEIOType.KEY_32_BIT})
#         'message_type': EIEIOType.KEY_PAYLOAD_32_BIT})

# build vertices

for x_position in range(0, max_x_element_id):
    for y_position in range(0, max_y_element_id):
        element = front_end.add_partitioned_vertex(
            HeatDemoVertexPartitioned,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
            label="heat_element at coords {}:{}".format(
                x_position, y_position))
        if vertices[x_position] is None:
            vertices[x_position] = list()
        vertices[x_position].append(element)

# build edges
for x_position in range(0, max_x_element_id):
    for y_position in range(0, max_y_element_id):

        # add a link from the injector to the heat element
        front_end.add_partitioned_edge(
            HeatDemoCommandEdge,
            {'pre_subvertex': command_injector,
             'post_subvertex': vertices[x_position][y_position],
             'n_keys': 3},
            label="injector edge for vertex {}"
                  .format(vertices[x_position][y_position].label),
            partition_id="COMMANDS")

        # add a link from the heat element to the live packet gatherer
        front_end.add_partitioned_edge(
            MultiCastPartitionedEdge,
            {'pre_subvertex': vertices[x_position][y_position],
             'post_subvertex': live_gatherer},
            label="gatherer edge from vertex {} to live packet gatherer"
                  .format(vertices[x_position][y_position].label),
            partition_id="GATHERER")

        # check for the likely hood for a N link (incoming to south)
        if (x_position + 1) < max_x_element_id:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position + 1][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.SOUTH},
                label="North edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position + 1][y_position]),
                partition_id="TRANSMISSION")
        else:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': command_injector,
                 'post_subvertex': vertices[x_position][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.NORTH},
                label="injected temp for north edge of fabric for heat element"
                      "{}".format(vertices[x_position][y_position]),
                partition_id="INJECTED_TEMP")

        # check for the likely hood for a E link
        if (y_position + 1) < max_y_element_id:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position][y_position + 1],
                 'direction': HeatDemoEdge.DIRECTIONS.WEST},
                label="East edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position][y_position + 1]),
                partition_id="TRANSMISSION")
        else:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': command_injector,
                 'post_subvertex': vertices[x_position][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.EAST},
                label="Injected temp for East edge of fabric for heat element"
                      " {}".format(vertices[x_position][y_position]),
                partition_id="INJECTED_TEMP")

        # check for the likely hood for a S link
        if (y_position - 1) >= 0:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position][y_position - 1],
                 'direction': HeatDemoEdge.DIRECTIONS.NORTH},
                label="South edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position][y_position - 1]),
                partition_id="TRANSMISSION")
        else:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': command_injector,
                 'post_subvertex': vertices[x_position][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.SOUTH},
                label="Injected temp for South edge of fabric for heat element"
                      " {}".format(vertices[x_position][y_position]),
                partition_id="INJECTED_TEMP")

        # check for the likely hood for a W link
        if (x_position - 1) >= 0:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': vertices[x_position][y_position],
                 'post_subvertex': vertices[x_position - 1][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.EAST},
                label="West edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position - 1][y_position]),
                partition_id="TRANSMISSION")
        else:
            front_end.add_partitioned_edge(
                HeatDemoEdge,
                {'pre_subvertex': command_injector,
                 'post_subvertex': vertices[x_position][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.WEST},
                label="Injected temp for West edge of fabric for heat element"
                      " {}".format(vertices[x_position][y_position]),
                partition_id="INJECTED_TEMP")


# Set up the live connection for sending and receiving spikes
# live_spikes_connection = LiveEventConnection(
#     receive_labels=["pop_forward", "pop_backward"],
#     send_labels=["spike_injector_forward", "spike_injector_backward"])

# Set up callbacks to occur when spikes are received
# live_spikes_connection.add_receive_callback("gatherer from heat elements",
#                                             receive_events)

front_end.run(10)
front_end.stop()
