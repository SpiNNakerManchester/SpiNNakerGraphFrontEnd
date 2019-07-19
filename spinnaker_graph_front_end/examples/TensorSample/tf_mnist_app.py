from pacman.model.graphs.machine import MachineEdge
from tensorflow.python.framework import tensor_util
import logging
import os
import numpy as np
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.TensorSample.mat_mul_vertex_non_dynamic import (MatMulVertexND)
from spinnaker_graph_front_end.examples.TensorSample.add_broadcast_vertex_non_dynamic import (AddBroadcastND)
from spinnaker_graph_front_end.examples.TensorSample.const_tensor_vertex_non_dynamic import (ConstTensorVertexND)
from spinnaker_graph_front_end.examples.TensorSample.softmax_vertex_non_dynamic import (SoftmaxND)
from spinnaker_graph_front_end.examples.TensorSample.log_vertex_non_dynamic import (LogND)
from spinnaker_graph_front_end.examples.TensorSample.mul_broadcast_vertex_non_dynamic import (MulBroadcastND)
from spinnaker_graph_front_end.examples.TensorSample.reduce_sum_non_dynamic import (ReduceSum)


import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
np.random.seed(0)

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


# front_end.setup(n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

# Parameters
learning_rate = 0.003
training_epochs = 1000
batch_size = 1
display_step = 1

(x_train, y_train), (x_test, y_test) = load_data('mnist.npz')

x_train = x_train.astype(float) / 255.
x_test = x_test.astype(float) / 255.

# One-hot transform of labels
y_train = convert_to_one_hot(y_train)
y_test = convert_to_one_hot(y_test)

# Graph inputs
X = tf.placeholder(tf.float32, [1, 784])
Y_ = tf.placeholder(tf.float32, [1, 10])

weights = np.zeros([784, 10])
bias = np.zeros([10])
W = tf.Variable(weights, dtype=np.float32)
b = tf.Variable(bias, dtype=np.float32)

sess = tf.Session()
sess.run(tf.global_variables_initializer())

# for i in range(2):

# Model
mul_res = tf.matmul(X, W)
Y = tf.nn.softmax(mul_res + b)

# Loss Function
log = tf.log(Y)
product = Y_ * log
cross_entropy = -tf.reduce_sum(product) # reduce_sum automatically created two nodes, sum and (const or reduction_indices)

optimizer = tf.train.GradientDescentOptimizer(learning_rate)
train_step = optimizer.minimize(cross_entropy)

batch_X, batch_Y = next_batch(batch_size, x_train, y_train)
batch_X_flat = np.reshape(batch_X, (-1, 784))
batch_X_flat = batch_X_flat.astype(np.float32)
batch_Y = batch_Y.astype(np.float32)

train_data = {X: batch_X_flat, Y_: batch_Y}

sess.run(train_step, feed_dict=train_data)

c = sess.run(cross_entropy, feed_dict=train_data)

writer = tf.summary.FileWriter('.')
writer.add_graph(tf.get_default_graph())
writer.flush()

graph = tf.get_default_graph()

const = {}
variable = {}
for n in tf.get_default_graph().as_graph_def().node:
    if 'Const' in n.name or n.name.endswith('initial_value'):
        if not n.attr["value"].tensor.tensor_shape.dim:
            const[n.name] = n.attr.get('value').tensor.int_val[0]
        else:
            const[n.name] = tensor_util.MakeNdarray(n.attr['value'].tensor)


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
    if 'MatMul' in graph._nodes_by_id[n_id].name:
        shape1, shape2 = get_input_shapes(n_id)
        vertices[n_id] = MatMulVertexND("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1, shape2)

    elif 'add'in graph._nodes_by_id[n_id].name:
        shape1, shape2 = get_input_shapes(n_id)
        vertices[n_id] = AddBroadcastND("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1, shape2)

    elif 'Softmax'in graph._nodes_by_id[n_id].name:
        shape1 = graph._nodes_by_id[n_id]._inputs._inputs[0].get_shape().as_list()
        vertices[n_id] = SoftmaxND("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1)

    elif 'Log'in graph._nodes_by_id[n_id].name:
        shape1 = graph._nodes_by_id[n_id]._inputs._inputs[0].get_shape().as_list()
        vertices[n_id] = LogND("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1)

    elif 'mul'in graph._nodes_by_id[n_id].name:
        shape1, shape2 = get_input_shapes(n_id)
        vertices[n_id] = MulBroadcastND("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1, shape2)

    elif 'Sum'in graph._nodes_by_id[n_id].name:
        shape1, shape2 = get_input_shapes(n_id)
        vertices[n_id] = ReduceSum("{} vertex ".format(graph._nodes_by_id[n_id].name), shape1, shape2)

    # constant operation
    elif 'Const' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = ConstTensorVertexND("{} vertex ".format(graph._nodes_by_id[n_id].name),
                                           const[graph._nodes_by_id[n_id].name])

    # Variable operation
    elif graph._nodes_by_id[n_id].name.endswith('initial_value'):
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
        logger.info("Mat Mul {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, oper_results))

front_end.stop()