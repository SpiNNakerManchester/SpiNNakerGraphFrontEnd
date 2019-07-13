from pacman.model.graphs.machine import MachineEdge
from tensorflow.python.framework import tensor_util
import logging
import os
import numpy as np
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.TensorSample.mat_mul_vertex_non_dynamic import (MatMulVertexND)
from spinnaker_graph_front_end.examples.TensorSample.mul_broadcast_vertex_non_dynamic import (MulBroadcastND)
from spinnaker_graph_front_end.examples.TensorSample.log_vertex_non_dynamic import (LogND)
from spinnaker_graph_front_end.examples.TensorSample.const_tensor_vertex_non_dynamic import (ConstTensorVertexND)
import tensorflow.compat.v1 as tf
# use functions of TensorFlow version 1 into TensorFlow version 2.
tf.disable_v2_behavior()

logger = logging.getLogger(__name__)


front_end.setup(n_chips_required=1, model_binary_folder=os.path.dirname(__file__))
tf.set_random_seed(0)

k = tf.constant([1, 2, 3, 4, 5, 6], shape=[2, 3], dtype=tf.float32)
m = tf.constant([7, 8, 9, 10, 11, 12], shape=[2, 3], dtype=tf.float32)

c = k * m

sess = tf.Session()
t = sess.run(c)

const = {}
for n in tf.get_default_graph().as_graph_def().node:
    if 'Const' in n.name:
        if not n.attr["value"].tensor.tensor_shape.dim:
            const[n.name] = n.attr.get('value').tensor.int_val[0]
        else:
            const[n.name] = tensor_util.MakeNdarray(n.attr['value'].tensor)

graph = tf.get_default_graph()

# List of spinnaker vertices
vertices = {}
inputs = {}


def store_input_node_ids (n_id):
    current_inputs = []
    if graph._nodes_by_id[n_id]._inputs:
        for index in graph._nodes_by_id[n_id]._inputs:
            current_inputs.append(index._id)
    inputs[n_id] = current_inputs


def get_input_shapes(n_id):
    sp1 = graph._nodes_by_id[n_id]._inputs._inputs[0].get_shape().as_list()
    sp2 = graph._nodes_by_id[n_id]._inputs._inputs[1].get_shape().as_list()
    return sp1, sp2


# Add Vertices
for n_id in graph._nodes_by_id:
    print('node id :', n_id, 'and name:', graph._nodes_by_id[n_id].name)
    # math operations
    if 'mul'in graph._nodes_by_id[n_id].name:
        shape1, shape2 = get_input_shapes(n_id)
        vertices[n_id] = MulBroadcastND("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1, shape2)

    # constant operation
    elif 'Const' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = ConstTensorVertexND("{} vertex ".format(graph._nodes_by_id[n_id].name),
                                           const[graph._nodes_by_id[n_id].name])
    else:
        break

    store_input_node_ids(n_id)

    vertices[n_id].name = graph._nodes_by_id[n_id].name
    front_end.add_machine_vertex_instance(vertices[n_id])

# Add Edges
for n_id in vertices:
    # Check if this vertex has inputs nodes
    if n_id in inputs :
        # Iterate over input ids of the nodes
        for input_key in inputs[n_id]:
            # add the edge
            front_end.add_machine_edge_instance(MachineEdge(vertices[input_key], vertices[n_id],
                                                label=vertices[input_key].name + ': to ' + vertices[n_id].name),
                                                "OPERATION_PARTITION")

sess.close()

print("run simulation")
front_end.run(1)

placements = front_end.placements()
txrx = front_end.transceiver()

print("read SDRAM after run")
for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, ConstTensorVertexND):
        const_value = placement.vertex.read(placement, txrx)
        logger.info("CONST {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, const_value))

    if isinstance(placement.vertex, MatMulVertexND):
        oper_results = placement.vertex.read(placement, txrx)
        logger.info("Mul Broadcast {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, oper_results))

front_end.stop()