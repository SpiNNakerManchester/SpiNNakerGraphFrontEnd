from pacman.model.graphs.machine import MachineEdge
from tensorflow.python.framework import tensor_util
import logging
import os
import unittest
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.TensorSample.mat_mul_vertex import (MatMulVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_tensor_vertex import (ConstTensorVertex)
import numpy as np
import mnistdata
import tensorflow.compat.v1 as tf
# use functions of TensorFlow version 1 into TensorFlow version 2.
tf.disable_v2_behavior()

logger = logging.getLogger(__name__)


front_end.setup(n_chips_required=1, model_binary_folder=os.path.dirname(__file__))
tf.set_random_seed(0)

mnist = mnistdata.read_data_sets("data", one_hot=True, reshape=False)  # 66 nodes

batch_X, batch_Y = mnist.train.next_batch(100)

XX = tf.reshape(batch_X, [-1, 784])

pixels = 255 * XX  # Now scale by 255

init = tf.global_variables_initializer()
sess = tf.Session()
p = sess.run(pixels)

v_batch_X = ConstTensorVertex("{} vertex ".format("batch_X"), pixels.astype(np.uint8))

print("run simulation")
front_end.run(1)

placements = front_end.placements()
txrx = front_end.transceiver()

print("read SDRAM after run")
# for placement in sorted(placements.placements,
#                         key=lambda p: (p.x, p.y, p.p)):
#
#     if isinstance(placement.vertex, ConstScalarVertex):
#         const_value = placement.vertex.read(placement, txrx)
#         logger.info("CONST {}, {}, {} > {}".format(
#             placement.x, placement.y, placement.p, const_value))
#
#     if isinstance(placement.vertex, OperationVertex):
#         oper_results = placement.vertex.read(placement, txrx)
#         logger.info("OPERATION {}, {}, {} > {}".format(
#             placement.x, placement.y, placement.p, oper_results))

front_end.stop()


