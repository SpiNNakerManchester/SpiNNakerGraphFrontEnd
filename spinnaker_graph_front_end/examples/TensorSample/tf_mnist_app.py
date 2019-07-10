from pacman.model.graphs.machine import MachineEdge
from tensorflow.python.framework import tensor_util
import logging
import os
import numpy as np
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.TensorSample.mat_mul_vertex import (MatMulVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_tensor_vertex import (ConstTensorVertex)
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

logger = logging.getLogger(__name__)


def load_data(path):
    with np.load(path) as f:
        x_train, y_train = f['x_train'], f['y_train']
        x_test, y_test = f['x_test'], f['y_test']
        return (x_train, y_train), (x_test, y_test)


def next_batch(num, data, labels):
    '''
    Return a total of `num` random samples and labels.
    '''
    idx = np.arange(0 , len(data))
    np.random.shuffle(idx)
    idx = idx[:num]
    data_shuffle = [data[ i] for i in idx]
    labels_shuffle = [labels[ i] for i in idx]

    return np.asarray(data_shuffle), np.asarray(labels_shuffle)


def convert_to_one_hot(y):
    result = np.zeros((y.size, 10))
    result[np.arange(y.size), y] = 1
    return result


front_end.setup(n_chips_required=1, model_binary_folder=os.path.dirname(__file__))
tf.set_random_seed(0)
np.random.seed(0)


(x_train, y_train), (x_test, y_test) = load_data('mnist.npz')

x_train = x_train.astype(float) / 255.
x_test = x_test.astype(float) / 255.

# One-hot transform of labels
y_train = convert_to_one_hot(y_train)
y_test = convert_to_one_hot(y_test)

W = np.zeros((784, 10))

b = np.zeros(10)

sess = tf.Session()

# for i in range(2):

batch_X, batch_Y = next_batch(10, x_train, y_train)
batch_X_temp = np.reshape(batch_X, (-1, 784))  # [-1, 784]
batch_X_temp.astype(np.float32)
pixels = tf.constant(batch_X_temp, tf.float32)
weights = tf.constant(W, tf.float32)

mul_res = tf.matmul(pixels, weights)
Y = tf.nn.softmax(mul_res + b)
t = sess.run(Y)

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


# Add Vertices
for n_id in graph._nodes_by_id:
    print('node id :', n_id, 'and name:', graph._nodes_by_id[n_id].name)
    # math operations
    if 'MatMul' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = MatMulVertex("{} vertex ".format(graph._nodes_by_id[n_id].name))

    # constant operation
    elif 'Const' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = ConstTensorVertex("{} vertex ".format(graph._nodes_by_id[n_id].name),
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

    if isinstance(placement.vertex, ConstTensorVertex):
        const_value = placement.vertex.read(placement, txrx)
        logger.info("CONST {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, const_value))

    if isinstance(placement.vertex, MatMulVertex):
        oper_results = placement.vertex.read(placement, txrx)
        logger.info("Mat Mul {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, oper_results))

front_end.stop()