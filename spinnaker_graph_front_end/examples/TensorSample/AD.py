
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

#
# x = tf.Variable(1.0, trainable=True, name = "x")
# y =  tf.square(x)
# z = tf.gradients([y], [x])

vec = tf.constant([1, 2, 3, 4])
multiply = tf.constant([3])

result = tf.tile(vec, multiply)

sess = tf.Session()
d=sess.run(result)

writer = tf.summary.FileWriter('.')
writer.add_graph(tf.get_default_graph())
writer.flush()