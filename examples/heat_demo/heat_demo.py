import os
import spynnaker_graph_front_end as front_end
from examples.heat_demo.heat_demo_vertex import HeatDemoVertex
from examples.heat_demo.heat_demo_edge import HeatDemoEdge
from examples import heat_demo

# set up the front end and ask for the detected machines dimensions
front_end.setup(graph_label="heat_demo_graph",  model_binary_folder=heat_demo)
dimenions = front_end.get_machine_dimensions()

machine_time_step = 1
time_scale_factor = 1

vertices = list()

#build vertices
for x_position in range(0, (dimenions['x'] * 4)):
    for y_position in range(0, (dimenions['y'] * 4)):

        element = HeatDemoVertex(
            label="heat_element at coords {}:{}".format(x_position, y_position),
            machine_time_step=machine_time_step,
            time_scale_factor=time_scale_factor)
        front_end.PartitionedVertex(
            HeatDemoVertex,
            {'label': "heat_element at coords {}:{}"
             .format(x_position, y_position),
             'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor})
        if vertices[x_position] is None:
            vertices[x_position] = list()
        vertices[x_position].append(element)

#build edges
for x_position in range(0, dimenions['x']):
    for y_position in range(0, dimenions['y']):
        # check for the likely hood for a N link
        if ((x_position + 1) % dimenions['x']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position + 1][y_position],
                 'label': "North edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position + 1][y_position]),
                 'direction': HeatDemoEdge.DIRECTIONS.NORTH})
        # check for the likely hood for a NE link
        if (((x_position + 1) % dimenions['x']) != 0 and
                    (y_position + 1) % dimenions['y'] != 0):
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position + 1][y_position + 1],
                 'label': "North East edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position + 1][y_position + 1]),
                 'direction': HeatDemoEdge.DIRECTIONS.NORTH_EAST})
        # check for the likely hood for a E link
        if ((y_position + 1) % dimenions['y']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position][y_position + 1],
                 'label': "East edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position][y_position + 1]),
                 'direction': HeatDemoEdge.DIRECTIONS.EAST})
        # check for the likely hood for a S link
        if ((y_position - 1) % dimenions['y']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position][y_position - 1],
                 'label': "South edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position][y_position - 1]),
                 'direction': HeatDemoEdge.DIRECTIONS.SOUTH})
        # check for the likely hood for a SW link
        if (((y_position - 1) % dimenions['y']) != 0 and
                (x_position - 1) % dimenions['x']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position - 1][y_position - 1],
                 'label': "South West edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position - 1][y_position - 1]),
                 'direction': HeatDemoEdge.DIRECTIONS.SOUTH_WEST})
        # check for the likely hood for a W link
        if ((x_position - 1) % dimenions['x']) != 0:
            front_end.PartitionedEdge(
                HeatDemoEdge,
                {'pre_vertex': vertices[x_position][y_position],
                 'post_vertex': vertices[x_position - 1][y_position],
                 'label': "West edge between heat elements {}:{}"
                          .format(vertices[x_position][y_position],
                                  vertices[x_position - 1][y_position]),
                 'direction': HeatDemoEdge.DIRECTIONS.WEST})

front_end.run(10000)
front_end.stop()