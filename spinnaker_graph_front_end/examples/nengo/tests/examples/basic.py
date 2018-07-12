import numpy as np
import nengo
from nengo.builder import Model
from nengo_spinnaker.node_io import Ethernet


def create_model():

    model = nengo.Network()
    with model:
        stimulus_A = nengo.Node([1], label='stim A')
        stimulus_B = nengo.Node(lambda t: np.sin(2*np.pi*t))
        ens = nengo.Ensemble(n_neurons=1000, dimensions=2)
        result = nengo.Ensemble(n_neurons=50, dimensions=1)
        nengo.Connection(stimulus_A, ens[0])
        nengo.Connection(stimulus_B, ens[1])
        nengo.Connection(
            ens, result, function=lambda x: x[0] * x[1], synapse=0.01)
    return model



if __name__ == '__main__':
    network = create_model()
    # build via nengo - spinnaker
    nengo_spinnaker_network_builder = Model()
    nengo_spinnaker_network_builder.build(network)