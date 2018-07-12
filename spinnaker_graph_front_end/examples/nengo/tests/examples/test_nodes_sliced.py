import nengo


def out_fun_1(val):
    assert val.size == 2
    return val * 2


def create_model():
    model = nengo.Network()
    with model:
        # Create the input node and an ensemble
        in_node = nengo.Node(
            lambda t: [0.1, 1.0, 0.2, -1.0], size_out=4, label="in_node")
        in_node_2 = nengo.Node(0.25, label="in_node_2")

        ens = nengo.Ensemble(400, 4, label="ens")
        ens2 = nengo.Ensemble(200, 2, label="ens2")

        # Create the connections
        nengo.Connection(in_node[::2], ens[[1, 3]], transform=.5,
                         function=out_fun_1)
        nengo.Connection(in_node_2[[0, 0]], ens2)

        # Probe the ensemble to ensure that the values are correct
        p = nengo.Probe(ens, synapse=0.05, label="probe")
        p2 = nengo.Probe(ens2, synapse=0.05, label="probe2")

    return model, [in_node], dict()
