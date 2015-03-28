"""
heat demo main entrance
"""
import spynnaker_graph_front_end as front_end
from spynnaker_graph_front_end import ReverseIpTagMultiCastSource
from spynnaker_graph_front_end import PartitionedEdge

from examples.heat_demo.heat_demo_vertex import HeatDemoVertexPartitioned
from examples.heat_demo.heat_demo_edge import HeatDemoEdge
from examples import heat_demo

# set up the front end and ask for the detected machines dimensions
front_end.setup(graph_label="heat_demo_graph", model_binary_folder=heat_demo)
dimenions = front_end.get_machine_dimensions()

machine_time_step = 1
time_scale_factor = 1
machine_name = "spinn-1.cs.man.ac.uk"
machine_port = 11111

vertices = [None] * (dimenions['x'] * 4)

command_injector = \
    front_end.PartitionedVertex(
        ReverseIpTagMultiCastSource,
        {'n_atoms': 3, 'machine_time_step': machine_time_step,
         'timescale_factor': time_scale_factor, 'label': "injector_from_vis",
         'host_ip_address': machine_name, 'host_port_number': machine_port})

# build vertices
for x_position in range(0, (dimenions['x'] * 4)):
    for y_position in range(0, (dimenions['y'] * 4)):
        element = front_end.PartitionedVertex(
            HeatDemoVertexPartitioned,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
            label="heat_element at coords {}:{}".format(x_position, y_position))
        if vertices[x_position] is None:
            vertices[x_position] = list()
        vertices[x_position].append(element)

# build edges
for x_position in range(0, dimenions['x']):
    for y_position in range(0, dimenions['y']):
        # add a link from the injecotr to the heat element
        front_end.PartitionedEdge(
            PartitionedEdge,
            {'pre_vertex': command_injector,
             'post_vertex': vertices[x_position][y_position]})
        # check for the likely hood for a N link
        if ((x_position + 1) % dimenions['x']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position + 1][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.NORTH},
                label="North edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position + 1][y_position]),)
        # check for the likely hood for a E link
        if ((y_position + 1) % dimenions['y']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position][y_position + 1],
                 'direction': HeatDemoEdge.DIRECTIONS.EAST},
                label="East edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position][y_position + 1]),)
        # check for the likely hood for a S link
        if ((y_position - 1) % dimenions['y']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position][y_position - 1],
                 'direction': HeatDemoEdge.DIRECTIONS.SOUTH},
                label="South edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position][y_position - 1]),)
        # check for the likely hood for a W link
        if ((x_position - 1) % dimenions['x']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position - 1][y_position],
                 'direction': HeatDemoEdge.DIRECTIONS.WEST},
                label="West edge between heat elements {}:{}"
                      .format(vertices[x_position][y_position],
                              vertices[x_position - 1][y_position]),)

front_end.run(10000)
front_end.stop()