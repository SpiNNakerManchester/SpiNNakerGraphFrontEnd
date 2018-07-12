import numpy as np

import nengo


def create_model():
    num_items = 5

    d_key = 2
    d_value = 4

    record_encoders = True

    rng = np.random.RandomState(seed=7)
    keys = nengo.dists.UniformHypersphere(surface=True).sample(
        num_items, d_key, rng=rng)
    values = nengo.dists.UniformHypersphere(surface=False).sample(
        num_items, d_value, rng=rng)

    intercept = (np.dot(keys, keys.T) - np.eye(num_items)).flatten().max()

    def cycle_array(x, period, dt=0.001):
        """Cycles through the elements"""
        i_every = int(round(period/dt))
        if i_every != period/dt:
            raise ValueError("dt (%s) does not divide period (%s)" % (
                dt, period))

        def f(t):
            i = int(round((t - dt)/dt))  # t starts at dt
            return x[(i/i_every)%len(x)]
        return f

    # Model constants
    n_neurons = 200
    dt = 0.001
    period = 0.3
    T = period*num_items*2

    # Model network
    model = nengo.Network()
    with model:

        # Create the inputs/outputs
        stim_keys = nengo.Node(
            output=cycle_array(keys, period, dt), label="stim_keys")
        stim_values = nengo.Node(
            output=cycle_array(values, period, dt), label="stim_values")
        learning = nengo.Node(
            output=lambda t: -int(t >= T/2), label="learning")
        recall = nengo.Node(size_in=d_value, label="recall")

        # Create the memory
        memory = nengo.Ensemble(
            n_neurons, d_key, intercepts=[intercept]*n_neurons,
            label="memory")

        # Learn the encoders/keys
        voja = nengo.Voja(post_tau=None, learning_rate=5e-2)
        conn_in = nengo.Connection(
            stim_keys, memory, synapse=None, learning_rule_type=voja)
        nengo.Connection(learning, conn_in.learning_rule, synapse=None)

        # Learn the decoders/values, initialized to a null function
        conn_out = nengo.Connection(
            memory, recall, learning_rule_type=nengo.PES(1e-3),
            function=lambda x: np.zeros(d_value))

        # Create the error population
        error = nengo.Ensemble(n_neurons, d_value, label="error")
        nengo.Connection(
            learning, error.neurons, transform=[[10.0]]*n_neurons,
            synapse=None)

        # Calculate the error and use it to drive the PES rule
        nengo.Connection(stim_values, error, transform=-1, synapse=None)
        nengo.Connection(recall, error, synapse=None)
        nengo.Connection(error, conn_out.learning_rule)

        # Setup probes
        p_keys = nengo.Probe(stim_keys, synapse=None, label="p_keys")
        p_values = nengo.Probe(stim_values, synapse=None, label="p_values")
        p_learning = nengo.Probe(learning, synapse=None, label="p_learning")
        p_error = nengo.Probe(error, synapse=0.005, label="p_error")
        p_recall = nengo.Probe(recall, synapse=None, label="p_recall")

        if record_encoders:
            p_encoders = nengo.Probe(
                conn_in.learning_rule, 'scaled_encoders',
                label="p_encoders")
    return model, list(), dict()

