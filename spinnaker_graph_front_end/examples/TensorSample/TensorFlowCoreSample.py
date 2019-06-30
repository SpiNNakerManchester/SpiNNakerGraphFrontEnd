## To visualize  python - m tensorboard.main - -logdir = / home / konst / Documents
## I can create my custom operation
#   https://www.tensorflow.org/guide/extend/op#define_the_ops_interface
## Here is the list of current available operations
#   https://gist.github.com/dustinvtran/cf34557fb9388da4c9442ae25c2373c9

from pacman.model.graphs.machine import MachineEdge
from tensorflow.python.framework import tensor_util
import logging
import os
import unittest
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.TensorSample.operation_vertex import (OperationVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_vertex import (ConstVertex)
import tensorflow.compat.v1 as tf
# use functions of TensorFlow version 1 into TensorFlow version 2.
tf.disable_v2_behavior()

logger = logging.getLogger(__name__)


class TestingTensorGraph(unittest.TestCase):

    def test_Tensor_graph(self):

        front_end.setup(n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

        # a = tf.constant(1, dtype=tf.int32)
        # b = tf.constant(2, dtype=tf.int32)
        # c = tf.constant(3, dtype=tf.int32)
        # d = tf.constant(4, dtype=tf.int32)
        # e = tf.constant(5, dtype=tf.int32)

        # constant_int_tensor = tf.constant(-255, shape=[1, 2, 3], dtype="int32")

        # 2-D tensor `a`
        # [[1, 2, 3],
        #  [4, 5, 6]]
        k = tf.constant([1, 2, 3, 4, 5, 6], shape=[2, 3])

        # 2-D tensor `b`
        # [[ 7,  8],
        #  [ 9, 10],
        #  [11, 12]]
        l = tf.constant([7, 8, 9, 10, 11, 12], shape=[3, 2])
        # p = tf.rank(k)
        # `a` * `b`
        # [[ 58,  64],
        #  [139, 154]]
        c = tf.matmul(k, l)

        # result = tf.matmul(k, l)
        # result = a+b
        # Launch the graph in a session.
        sess = tf.Session()

        # sess.run(tf.global_variables_initializer())
        t = sess.run(c)

        const = {}
        for n in tf.get_default_graph().as_graph_def().node:
            if 'Const' in n.name:
                if not n.attr["value"].tensor.tensor_shape.dim:
                    const[n.name] = n.attr.get('value').tensor.int_val[0]
                else:
                    const[n.name] = tensor_util.MakeNdarray(n.attr['value'].tensor)
                    # tensor_shape = [x.size for x in n.attr["value"].tensor.tensor_shape.dim]
                    # const[n.name] = n.attr.get('value').tensor.tensor_content  # Binary form String of the tensor

        graph = tf.get_default_graph()

        # List of spinnaker vertices
        vertices = {}
        inputs = {}

        operations = { "add": 1,
                       "mul": 2,
                       "sub": 3,
                       "MatMul": 4,
                       # "truediv":5,
                       # "Placeholder"
                       }

        def store_spinnaker_vertices(n_id, oper_type):
            vertices[n_id] = OperationVertex("{} vertex ".format(graph._nodes_by_id[n_id].name), oper_type)

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
            if 'add' in graph._nodes_by_id[n_id].name:
                store_spinnaker_vertices(n_id, operations["add"])

            elif 'mul' in graph._nodes_by_id[n_id].name:
                store_spinnaker_vertices(n_id, operations["mul"])

            elif 'sub' in graph._nodes_by_id[n_id].name:
                store_spinnaker_vertices(n_id, operations["sub"])

            elif 'MatMul' in graph._nodes_by_id[n_id].name:
                store_spinnaker_vertices(n_id, operations["MatMul"])

            # elif 'truediv' == graph._nodes_by_id[n_id].name:
            #     store_spinnaker_vertices(n_id, operations["truediv"])

            # constant operation
            elif 'Const' in graph._nodes_by_id[n_id].name:
                vertices[n_id] = ConstVertex("{} vertex ".format(graph._nodes_by_id[n_id].name),
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

            if isinstance(placement.vertex, ConstVertex):
                const_value = placement.vertex.read(placement, txrx)
                logger.info("CONST {}, {}, {} > {}".format(
                    placement.x, placement.y, placement.p, const_value))
                self.assertEqual(const_value,3)

            if isinstance(placement.vertex, OperationVertex):
                oper_results = placement.vertex.read(placement, txrx)
                logger.info("OPERATION {}, {}, {} > {}".format(
                    placement.x, placement.y, placement.p, oper_results))

        front_end.stop()


if __name__ == '__main__':
    unittest.main()