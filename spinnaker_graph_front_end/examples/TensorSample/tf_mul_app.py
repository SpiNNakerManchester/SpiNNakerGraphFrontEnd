from pacman.model.graphs.machine import MachineEdge
import logging
import os
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.TensorSample.mul_scalar_vertex import (MulVertex)
from spinnaker_graph_front_end.examples.TensorSample.const_scalar_vertex import (ConstScalarVertex)
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()

logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))


a = tf.constant(9, dtype=tf.int32)
b = tf.constant(13, dtype=tf.int32)
c = tf.constant(7, dtype=tf.int32)
d = tf.constant(1, dtype=tf.int32)

result = a * b * c * d

# Launch the graph in a session.
sess = tf.Session()
sess.run(result)

const = {}
for n in tf.get_default_graph().as_graph_def().node:
    if 'Const' in n.name:
        const[n.name] = n.attr.get('value').tensor.int_val[0]

graph = tf.get_default_graph()

# List of spinnaker vertices
vertices = {}
inputs = {}

# Store input node ids for the current node
def store_input_node_ids(n_id):
    current_inputs = []
    if graph._nodes_by_id[n_id]._inputs:
        for index in graph._nodes_by_id[n_id]._inputs:
            current_inputs.append(index._id)
    inputs[n_id] = current_inputs


# Add Vertices
for n_id in graph._nodes_by_id:
    print('node id :', n_id, 'and name:', graph._nodes_by_id[n_id].name)
    # addition operation
    if 'mul' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = MulVertex("MulVertex vertex {}".format(graph._nodes_by_id[n_id].name))

    # constant operation
    elif 'Const' in graph._nodes_by_id[n_id].name:
        vertices[n_id] = ConstScalarVertex("Const vertex {}".format(graph._nodes_by_id[n_id].name),
                                           const[graph._nodes_by_id[n_id].name])

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
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[input_key], vertices[n_id],
                                label=vertices[input_key].name + ': to ' + vertices[n_id].name),
                                "OPERATION")

print("run simulation")
front_end.run(1)

placements = front_end.placements()
txrx = front_end.transceiver()

print("read SDRAM after run")
for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):

    if isinstance(placement.vertex, ConstScalarVertex):
        const_value = placement.vertex.read(placement, txrx)
        logger.info("CONST {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, const_value))

    if isinstance(placement.vertex, MulVertex):
        addition_results = placement.vertex.read(placement, txrx)
        logger.info("MUL {}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, addition_results))

front_end.stop()