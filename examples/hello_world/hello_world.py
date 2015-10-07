"""
heat demo main entrance allows users to run the heat demo on the tool chain
"""

# graph front end imports
import spynnaker_graph_front_end as front_end

# example imports
from hello_world_vertex import HelloWorldVertex


from spinnman.messages.eieio.eieio_type import EIEIOType

# spinn front end common imports
from spinn_front_end_common.utility_models.live_packet_gather import \
    LivePacketGather


from spynnaker_graph_front_end import MultiCastPartitionedEdge

# method for dealing with heat element events
# def receive_events(label, time, neuron_ids):
#     pass

a = file("/home/gmtuca/Spinnaker/Repositories/SpiNNakerGraphFrontEnd/examples/model_binaries/hello_world.aplx")

# set up the front end and ask for the detected machines dimensions
front_end.setup(graph_label="hello_world",
                model_binary_module=a)
dimenions = front_end.get_machine_dimensions()

machine_time_step = 1000
time_scale_factor = 1
machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"

# hard code dimensions here (useful for debug) (chip based)
x_dimension = dimenions['x']
y_dimension = dimenions['y']

max_x_element_id = x_dimension * 4
max_y_element_id = y_dimension * 4

# overrwide dimensions
max_x_element_id = 3
max_y_element_id = 3

vertices = [None] * (x_dimension * 4)

for x_position in range(0, max_x_element_id):
    for y_position in range(0, max_y_element_id):
        element = front_end.add_partitioned_vertex(
            HelloWorldVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor})
        if vertices[x_position] is None:
            vertices[x_position] = list()
        vertices[x_position].append(element)

front_end.run(10)
front_end.stop()
