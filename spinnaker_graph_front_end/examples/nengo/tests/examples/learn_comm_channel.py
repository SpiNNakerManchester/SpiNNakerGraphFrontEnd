import numpy as np

import nengo
from nengo.processes import WhiteSignal


def create_model():
    dimensions = 4
    model = nengo.Network()
    with model:
        num_neurons = dimensions * 30
        inp = nengo.Node(
            WhiteSignal(num_neurons, high=5), size_out=dimensions,
            label="white_noise")
        pre = nengo.Ensemble(
            num_neurons, dimensions=dimensions, label="pre")
        nengo.Connection(inp, pre)
        post = nengo.Ensemble(
            num_neurons, dimensions=dimensions, label="post")
        conn = nengo.Connection(
            pre, post, function=lambda x: np.random.random(dimensions))
        inp_p = nengo.Probe(inp, label="inp_p")
        pre_p = nengo.Probe(pre, synapse=0.01, label="pre_p")
        post_p = nengo.Probe(post, synapse=0.01, label="post_p")

        error = nengo.Ensemble(
            num_neurons, dimensions=dimensions, label="error")
        error_p = nengo.Probe(error, synapse=0.03, label="error_p")

        # Error = actual - target = post - pre
        nengo.Connection(post, error)
        nengo.Connection(pre, error, transform=-1)

        # Add the learning rule to the connection
        conn.learning_rule_type = nengo.PES()

        # Connect the error into the learning rule
        nengo.Connection(error, conn.learning_rule)
    return model
