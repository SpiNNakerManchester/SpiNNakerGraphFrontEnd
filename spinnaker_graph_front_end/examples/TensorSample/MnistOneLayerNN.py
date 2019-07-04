#!/usr/bin/env python
# coding: utf-8


import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import numpy as np

mnist = input_data.read_data_sets("MNIST_data/", one_hot=True)

# Initialize variables

# None will be the size of the batch

X = tf.placeholder(tf.float32, [None, 28, 28, 1])

W = tf.Variable(tf.zeros([784, 10]))

b = tf.Variable(tf.zeros([10]))

init = tf.global_variables_initializer()

XX = tf.reshape(X, [-1, 784])

mul_res = tf.matmul(XX, W)



#Model

Y = tf.nn.softmax(mul_res + b)

#Placeholder for the correct answers

Y_ = tf.placeholder(tf.float32, [None,10])


#Loss Function

cross_entropy = -tf.reduce_sum(Y_ * tf.log(Y))

#cross_entropy

#% of correct answers found in batch

is_correct = tf.equal(tf.argmax(Y,1), tf.argmax(Y_,1))

accuracy = tf.reduce_mean(tf.cast(is_correct, tf.float32))

#accuracy

#learning rate 0.003

optimizer = tf.train.GradientDescentOptimizer(0.003)

#optimizer

train_step = optimizer.minimize(cross_entropy)

writer = tf.summary.FileWriter('.')
writer.add_graph(tf.get_default_graph())
writer.flush()

#train_step

## Run Session

sess = tf.Session()

sess.run(init)

for i in range(10000):
    #load batch of images and correct answers

    batch_X, batch_Y = mnist.train.next_batch(100)

    #batch_X.shape

    batch_X = np.reshape(batch_X, (-1, 28, 28, 1))

    batch_Y = np.reshape(batch_Y, (-1, 10))

    train_data = {X: batch_X, Y_: batch_Y}

    #train

    sess.run(train_step, feed_dict = train_data)

    #success ?

    a,c = sess.run([accuracy, cross_entropy], feed_dict=train_data)

    #success on test data ?

    test_batch_X = np.reshape(mnist.test.images, (-1, 28, 28, 1))

    test_batch_Y = np.reshape(mnist.test.labels, (-1, 10))

    test_data = {X:test_batch_X, Y_:test_batch_Y}

    a,c = sess.run([accuracy, cross_entropy], feed_dict=test_data)


# In[4]:


a

