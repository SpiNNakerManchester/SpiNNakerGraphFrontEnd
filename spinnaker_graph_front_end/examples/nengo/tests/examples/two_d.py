import numpy as np
import nengo


def create_model():

    model = nengo.Network()
    with model:
        stimulus = nengo.Node(lambda t: (np.sin(t), np.cos(t)))
        ens = nengo.Ensemble(n_neurons=1000, dimensions=2)
        nengo.Connection(stimulus, ens)
    return model, list(), dict()
