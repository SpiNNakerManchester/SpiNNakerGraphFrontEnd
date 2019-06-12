## The Client TensorFlow program builds the computational graph.
## The Client TensorFlow sends the graph definition to the Distributed Master
## TensorFlow core programs consist of A) Building the graph tf.Graph and
#                                      B) Running the computational graph in tf.Session
## To visualize  python - m tensorboard.main - -logdir = / home / konst / Documents
## I can create my custom operation
#   https://www.tensorflow.org/guide/extend/op#define_the_ops_interface
## Here is the list of current available operations
#   https://gist.github.com/dustinvtran/cf34557fb9388da4c9442ae25c2373c9

# Tensors are the Edges of the graph which are multidimensional Arrays
# The logic is to build the TensorFlow graph first and then execute it as a Tensor.
# The data that pass between the operations are tensors.

# From code perspective a Tensor instance is a symbolic handle of the outputs of an Operation, so
# describes how to handle one output of an operation when the session will run.
# The tensor instance will be passed as input to another Operation.


from pacman.model.graphs.machine import MachineEdge
import logging
import os
import spinnaker_graph_front_end as front_end
import tensorflow as tf
from spinnaker_graph_front_end.examples.TensorSample.add_vertex import (AdditionVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_vertex import (ConstVertex)


logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

# Create 3 constant operations , one addition operation, then one extra addition
# here is just a representation of the graph.

a = tf.constant(19, dtype=tf.int32)
b = tf.constant(23, dtype=tf.int32)
# c = tf.constant(65, dtype=tf.int32)
result = a + b
# total = result + c

graph = tf.get_default_graph()

# string formatters in python:   .format  , ex: '{} {}'.format(1, 2) , output: 1 2

# First I wll create all the vertices in python representation of spinnaker and then I will create the edges
# I have to check in the future if we know the sequence that nodes by id are store in tensorflow , so in case
# that the first id nodes are always just inputs to other nodes we do not have to worry about the edge.
# Here the representation of edges are going to be created in the loop when we access a node that gets input Tensors

# The underscore prefix is meant as a hint to another programmer that a variable or method
# starting with a single underscore is intended for internal use

# Number of nodes in TensorFlow graph
number_of_nodes = graph._nodes_by_id.__len__()
# List of spinnaker vertices

vertices = {}
inputs = {}


# Add Vertices
for n_id in graph._nodes_by_id:
    print('node id :', n_id, 'and name:', graph._nodes_by_id[n_id].name)
    # in case of addition operation
    if 'add' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = AdditionVertex("Addition vertex {}".format(graph._nodes_by_id[n_id].name))
        # Store input node ids for the current node
        current_inputs = []
        if graph._nodes_by_id[n_id]._inputs:
            for index in graph._nodes_by_id[n_id]._inputs:
                current_inputs.append(index._id)
        inputs[n_id] = current_inputs

    # in case of constant operation
    elif 'Const' in graph._nodes_by_id[n_id].name:
        constant_sample = n_id
        vertices[n_id] = ConstVertex("Const vertex {}".format(graph._nodes_by_id[n_id].name), constant_sample)

    vertices[n_id].name = graph._nodes_by_id[n_id].name
    front_end.add_machine_vertex_instance(vertices[n_id])


# Add Edges
for n_id in vertices:
    # Check if this vertex has inputs nodes
    if n_id in inputs :
        # Iterate over input ids of the nodes
        for input_key in inputs:
            for input_node_id in inputs[input_key]:
                # add the edge
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[input_node_id], vertices[n_id],
                                label=vertices[input_node_id].name + ': to ' + vertices[n_id].name),
                    "ADDITION_PARTITION")

# Run for 2 milliseconds
print("run simulation")
front_end.run(1)

placements = front_end.placements()
txrx = front_end.transceiver()

print("read the SDRAM after the simulation run")
for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):
    # Kostas : After the run of the simulation, read
    # from SDRAM all the texts that were stored in SDRAM.
    if isinstance(placement.vertex, ConstVertex):
        const_value = placement.vertex.read(placement, txrx)
        logger.info("CONST {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, const_value))

    if isinstance(placement.vertex, AdditionVertex):
        addition_results = placement.vertex.read(placement, txrx)
        logger.info("ADDITION {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, addition_results))

front_end.stop()