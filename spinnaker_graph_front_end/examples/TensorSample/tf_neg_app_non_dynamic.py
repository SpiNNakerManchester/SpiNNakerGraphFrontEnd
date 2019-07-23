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
from spinnaker_graph_front_end.examples.TensorSample.const_scalar_vertex import (ConstScalarVertex)
from spinnaker_graph_front_end.examples.TensorSample.tf_fill_vertex import (FillVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_empty_vertex import (ConstEmptyVertex)
from spinnaker_graph_front_end.examples.TensorSample.tf_neg_vertex import (NegVertex)


import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
np.random.seed(0)

logger = logging.getLogger(__name__)

front_end.setup(n_chips_required=1, model_binary_folder=os.path.dirname(__file__))
tf.set_random_seed(0)

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


def from_tensor_get_operation_name(tensor_name):
    return tensor_name.split(sep=':')[0]

# Parameters
learning_rate = 0.003
training_epochs = 1000
batch_size = 2
display_step = 1

(x_train, y_train), (x_test, y_test) = load_data('mnist.npz')

x_train = x_train.astype(float) / 255.
x_test = x_test.astype(float) / 255.

# One-hot transform of labels
y_train = convert_to_one_hot(y_train)
y_test = convert_to_one_hot(y_test)

# Graph inputs
X = tf.placeholder(tf.float32, [batch_size, 784])
Y_ = tf.placeholder(tf.float32, [batch_size, 10])  # Placeholder for the correct answers

W = tf.Variable(np.zeros([784, 10], dtype=np.float32))
b = tf.Variable(np.zeros([10], dtype=np.float32))

init = tf.global_variables_initializer()

# Model
Y = tf.nn.softmax(tf.matmul(X, W) + b)

# Loss Function
cross_entropy = -tf.reduce_sum(Y_ * tf.log(Y))

optimizer = tf.train.GradientDescentOptimizer(learning_rate)
train_step = optimizer.minimize(cross_entropy)

writer = tf.summary.FileWriter('.')
writer.add_graph(tf.get_default_graph())
writer.flush()

sess = tf.Session()
sess.run(init)
batch_X, batch_Y = next_batch(batch_size, x_train, y_train)

batch_X = np.reshape(batch_X, (-1, 784))

batch_X = batch_X.astype(np.float32)
batch_Y = batch_Y.astype(np.float32)

train_data = {X: batch_X, Y_: batch_Y}

sess.run(train_step, feed_dict=train_data)

c = sess.run(cross_entropy, feed_dict=train_data)

graph = tf.get_default_graph()

const = {}
variable = {}
for n in tf.get_default_graph().as_graph_def().node:
    if n.op == 'Const':
        if n.name == 'gradients/grad_ys_0':
            const[n.name] = n.attr.get('value').tensor.float_val[0]
        elif n.name == 'gradients/Shape':
            const[n.name] = []
        else:
            if not n.attr["value"].tensor.tensor_shape.dim:
                if len(n.attr.get('value').tensor.float_val):
                    const[n.name] = n.attr.get('value').tensor.float_val[0]
                if len(n.attr.get('value').tensor.int_val):
                    const[n.name] = n.attr.get('value').tensor.int_val[0]
            else:
                const[n.name] = tensor_util.MakeNdarray(n.attr['value'].tensor)


# List of spinnaker vertices
vertices = {}
inputs = {}


def store_input_node_names (name):
    current_inputs = []
    if graph._nodes_by_name[name]._inputs:
        for n in graph._nodes_by_name[name]._inputs:  # The node
            op_name = from_tensor_get_operation_name(n.name)
            current_inputs.append(op_name)
    inputs[name] = current_inputs


# Add Vertices
for n in tf.get_default_graph().as_graph_def().node:
    # print('node id :', n_id, 'and name:', graph._nodes_by_id[n_id].name)
    # math operations

    if  n.name == 'gradients/Shape' :
        vertices[n.name] = ConstEmptyVertex("{} vertex ".format(n.name),
                                             const[n.name])

    elif n.name == 'gradients/grad_ys_0':
        vertices[n.name] = ConstScalarVertex("{} vertex ".format(n.name),
                                           int(const[n.name]))  # when the floats
                                                                                       # are handled in C the cast to int will be removed
    elif n.name == 'gradients/Fill':
        vertices[n.name] = FillVertex("{} vertex ".format(n.name))

    elif n.name == 'gradients/Neg_grad/Neg':
        vertices[n.name] = NegVertex("{} vertex ".format(n.name))

    else:
        continue

    store_input_node_names(n.name)
    front_end.add_machine_vertex_instance(vertices[n.name])

# Add Edges
for name in vertices:
    # Check if this vertex has inputs nodes
    if name in inputs :
        # Iterate over input ids of the nodes
        for n in inputs[name]:
            # add the edge
            front_end.add_machine_edge_instance(MachineEdge(vertices[n], vertices[name],
                                                label= n + ': to ' + name),
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