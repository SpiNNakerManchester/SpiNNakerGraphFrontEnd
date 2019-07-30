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


def get_input_shapes(name):
    sp1 = graph._nodes_by_name[name]._inputs._inputs[0].get_shape().as_list()
    sp2 = graph._nodes_by_name[name]._inputs._inputs[1].get_shape().as_list()
    return sp1, sp2


# Parameters
learning_rate = 0.003
training_epochs = 1000
batch_size = 100
display_step = 1

(x_train, y_train), (x_test, y_test) = load_data('mnist.npz')

x_train = x_train.astype(float) / 255.
x_test = x_test.astype(float) / 255.

# One-hot transform of labels
y_train = convert_to_one_hot(y_train)
y_test = convert_to_one_hot(y_test)

# Graph inputs
X = tf.placeholder(tf.float32, [None, 784])
Y_ = tf.placeholder(tf.float32, [None, 10])  # Placeholder for the correct answers

W = tf.Variable(tf.zeros([784, 10]), dtype=np.float32)
b = tf.Variable(tf.zeros([10]), dtype=np.float32)

init = tf.global_variables_initializer()

# Model
Y = tf.nn.softmax(tf.matmul(X, W) + b)

# Loss Function
cross_entropy = -tf.reduce_sum(Y_ * tf.log(Y))

# is_correct and accuracy are calculated just for display
is_correct = tf.equal(tf.argmax(Y,1), tf.argmax(Y_, 1))
accuracy = tf.reduce_mean(tf.cast(is_correct, tf.float32))

optimizer = tf.train.GradientDescentOptimizer(learning_rate)
train_step = optimizer.minimize(cross_entropy)

#train_step

writer = tf.summary.FileWriter('.')
writer.add_graph(tf.get_default_graph())
writer.flush()

# Run Session

sess = tf.Session()
sess.run(init)

graph = tf.get_default_graph()

# List of spinnaker vertices
vertices = {}
inputs = {}

# Write the training nodes
training_nodes = []
for n in tf.get_default_graph().as_graph_def().node:
    training_nodes.append(n.name)


def store_input_node_names (name):
    current_inputs = []
    if graph._nodes_by_name[name]._inputs:
        for n in graph._nodes_by_name[name]._inputs:  # The node
            op_name = from_tensor_get_operation_name(n.name)
            current_inputs.append(op_name)
    inputs[name] = current_inputs


final_weight=0
final_bias=0

for i in range(training_epochs):

    batch_X, batch_Y = next_batch(batch_size, x_train, y_train)

    batch_X = np.reshape(batch_X, (-1, 784))

    batch_X = batch_X.astype(np.float32)
    batch_Y = batch_Y.astype(np.float32)

    train_data = {X: batch_X, Y_: batch_Y}

    sess.run(train_step, feed_dict=train_data)
    c = sess.run(cross_entropy, feed_dict=train_data)
    print(c)
    a = sess.run([accuracy], feed_dict=train_data)

    a, c = sess.run([accuracy, cross_entropy], feed_dict=train_data)

    print(a)
    print(c)

    if i == training_epochs-1:
        final_weight = sess.run(W)
        final_bias = sess.run(b)

one_digit = np.reshape(x_test[0], (-1, 784))
one_digit = tf.constant(one_digit, dtype = tf.float32)

# one_digit_label = y_test[0]
# one_digit_label = tf.constant(one_digit_label, dtype = tf.float32)

final_weight = tf.constant(final_weight, dtype = tf.float32)
final_bias = tf.constant(final_bias, dtype = tf.float32)


prediction = tf.matmul(one_digit, final_weight) + final_bias
pred_max = tf.argmax(input=prediction, axis=1)
# test_max = tf.argmax(input=one_digit_label, axis=0)

# result = tf.equal(pred_max, test_max)

const = {}
for n in tf.get_default_graph().as_graph_def().node:
    if n.op == 'Const':
        if not n.attr["value"].tensor.tensor_shape.dim:
            if len(n.attr.get('value').tensor.float_val):
                const[n.name] = n.attr.get('value').tensor.float_val[0]
            if len(n.attr.get('value').tensor.int_val):
                const[n.name] = n.attr.get('value').tensor.int_val[0]
        else:
            const[n.name] = tensor_util.MakeNdarray(n.attr['value'].tensor)

for n in tf.get_default_graph().as_graph_def().node:
    print('name:', n.name)

    # Convert only the testing nodes
    if n.name not in training_nodes:

        if 'MatMul' in n.name:
            shape1, shape2 = get_input_shapes(n.name)
            vertices[n.name] = MatMulVertexND("{} vertex ".format(n.name), shape1, shape2)

        elif 'add' in n.name:
            shape1, shape2 = get_input_shapes(n.name)
            vertices[n.name] = AddBroadcastND("{} vertex ".format(n.name), shape1, shape2)

        elif 'Const' in n.name:
            vertices[n.name] = ConstTensorVertexND("{} vertex ".format(n.name), const[n.name])

        else:
            continue

        store_input_node_names(n.name)
        front_end.add_machine_vertex_instance(vertices[n.name])

    else:
        continue



# Add Edges
for name in vertices:
    # Check if this vertex has inputs nodes
    if name in inputs:
        # Iterate over input ids of the nodes
        for n in inputs[name]:
            # add the edge
            front_end.add_machine_edge_instance(MachineEdge(vertices[n], vertices[name],
                                                            label=n + ': to ' + name),
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

        # # MatMul
        # shape1 = [1, 784]
        # shape2 = [784, 10]
        # matMul = MatMulVertexND("{} vertex ".format("MatMul"), shape1, shape2)
        #
        # # Add Broadcast
        # matMul_shape = [1, 10]
        # bias_shape = [1, 10]
        # add_broadcast_res = AddBroadcastND("{} vertex ".format("AddBroadcastND"), matMul_shape, bias_shape)

