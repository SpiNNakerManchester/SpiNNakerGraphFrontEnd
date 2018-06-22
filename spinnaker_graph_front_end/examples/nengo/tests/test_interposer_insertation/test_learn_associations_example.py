

import numpy as np

import nengo


import unittest

from nengo.cache import NoDecoderCache
from nengo_spinnaker.builder import Model
from nengo_spinnaker.node_io import Ethernet

from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.\
    nengo_application_graph_builder import NengoApplicationGraphBuilder
from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.nengo_utilise_interposers import \
    NengoUtiliseInterposers
from spinnaker_graph_front_end.examples.nengo.tests.test_utilities import \
    compare_against_the_nengo_spinnaker_and_gfe_impls


class TestAppGraphBuilder(unittest.TestCase):

    def setUp(self):
        num_items = 5

        d_key = 2
        d_value = 4

        spinnaker = True
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
        return model

    def test_application_graph_builder(self):

        # build via gfe nengo spinnaker
        network = TestAppGraphBuilder.setUp(self)
        app_graph_builder = NengoApplicationGraphBuilder()
        (app_graph, host_network, nengo_to_app_graph_map,
         random_number_generator) = app_graph_builder(
            nengo_network=network, extra_model_converters={},
            machine_time_step=1.0, nengo_node_function_of_time=False,
            nengo_node_function_of_time_period=None,
            nengo_random_number_generator_seed=None,
            decoder_cache=NoDecoderCache(),
            utilise_extra_core_for_output_types_probe=True)
        interposer_installer = NengoUtiliseInterposers()
        app_graph = interposer_installer(
            app_graph, nengo_to_app_graph_map, random_number_generator)

        # build via nengo - spinnaker
        io_controller = Ethernet()
        builder_kwargs = io_controller.builder_kwargs
        nengo_spinnaker_network_builder = Model()
        nengo_spinnaker_network_builder.build(network, **builder_kwargs)
        nengo_spinnaker_network_builder.add_transposters()
        nengo_operators = dict()
        nengo_operators.update(
            nengo_spinnaker_network_builder.object_operators)
        nengo_operators.update(io_controller._sdp_receivers)
        nengo_operators.update(io_controller._sdp_transmitters)

        compare_against_the_nengo_spinnaker_and_gfe_impls(
            nengo_operators, nengo_to_app_graph_map,
            nengo_spinnaker_network_builder.connection_map, app_graph,
            nengo_spinnaker_network_builder)

        print "nengo_to_operator map contains:"
        for nengo_obj in nengo_to_app_graph_map:
            print "{}:{}".format(nengo_obj, nengo_to_app_graph_map[nengo_obj])

        print(app_graph, host_network, nengo_to_app_graph_map,
              random_number_generator)
