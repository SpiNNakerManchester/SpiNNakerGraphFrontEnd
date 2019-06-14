## To visualize  python - m tensorboard.main - -logdir = / home / konst / Documents
## I can create my custom operation
#   https://www.tensorflow.org/guide/extend/op#define_the_ops_interface
## Here is the list of current available operations
#   https://gist.github.com/dustinvtran/cf34557fb9388da4c9442ae25c2373c9

from pacman.model.graphs.machine import MachineEdge
import logging
import os
import spinnaker_graph_front_end as front_end
import tensorflow as tf
from spinnaker_graph_front_end.examples.TensorSample.operation_vertex import (OperationVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_vertex import (ConstVertex)


logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))


a = tf.constant(1, dtype=tf.int32)
b = tf.constant(5, dtype=tf.int32)
c = tf.constant(3, dtype=tf.int32)
# d = tf.constant(4, dtype=tf.int32)


result = a + b + c

# Launch the graph in a session.
sess = tf.Session()
sess.run(result)

const = {}
for n in tf.get_default_graph().as_graph_def().node:
    if 'Const' in n.name:
        const[n.name] = n.attr.get('value').tensor.int_val[0]

graph = tf.get_default_graph()

# List of spinnaker vertices
vertices = {}
inputs = {}


operations = { "add": 1,
               "mul": 2}

# Add Vertices
for n_id in graph._nodes_by_id:
    print('node id :', n_id, 'and name:', graph._nodes_by_id[n_id].name)
    # math operation
    if 'add' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = OperationVertex("{} vertex ".format(graph._nodes_by_id[n_id].name), operations["add"])
        # Store input node ids for the current node
        current_inputs = []
        if graph._nodes_by_id[n_id]._inputs:
            for index in graph._nodes_by_id[n_id]._inputs:
                current_inputs.append(index._id)
        inputs[n_id] = current_inputs

    if 'mul' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = OperationVertex("{} vertex ".format(graph._nodes_by_id[n_id].name), operations["mul"])
        # Store input node ids for the current node
        current_inputs = []
        if graph._nodes_by_id[n_id]._inputs:
            for index in graph._nodes_by_id[n_id]._inputs:
                current_inputs.append(index._id)
        inputs[n_id] = current_inputs

    # constant operation
    elif 'Const' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = ConstVertex("{} vertex ".format(graph._nodes_by_id[n_id].name),
                                     const[graph._nodes_by_id[n_id].name])

    vertices[n_id].name = graph._nodes_by_id[n_id].name
    front_end.add_machine_vertex_instance(vertices[n_id])


# Add Edges
for n_id in vertices:
    # Check if this vertex has inputs nodes
    if n_id in inputs :
        # Iterate over input ids of the nodes
        for input_key in inputs[n_id]:
                # add the edge
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[input_key], vertices[n_id],
                                label=vertices[input_key].name + ': to ' + vertices[n_id].name),
                    "OPERATION_PARTITION")

print("run simulation")
front_end.run(1)

placements = front_end.placements()
txrx = front_end.transceiver()

print("read SDRAM after run")
for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, ConstVertex):
        const_value = placement.vertex.read(placement, txrx)
        logger.info("CONST {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, const_value))

    if isinstance(placement.vertex, OperationVertex):
        oper_results = placement.vertex.read(placement, txrx)
        logger.info("OPERATION {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, oper_results))

front_end.stop()