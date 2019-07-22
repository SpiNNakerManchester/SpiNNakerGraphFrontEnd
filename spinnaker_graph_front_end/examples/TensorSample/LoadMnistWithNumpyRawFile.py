#!/usr/bin/env python
# coding: utf-8

import numpy as np
import tensorflow as tf
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
np.random.seed(0)


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

## Run Session

sess = tf.Session()
sess.run(init)


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