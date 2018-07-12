import numpy as np

import nengo


def create_model():
    dimension = 9

    model = nengo.Network()
    with model:
        for i in range(dimension):
            def waves(t, i=i):
                return np.sin(t + np.arange(i + 1) * 2 * np.pi / (i + 1))
            _ = nengo.Node(waves)
    return model, list(), dict()
