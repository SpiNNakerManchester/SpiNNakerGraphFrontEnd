import unittest

from nengo.cache import NoDecoderCache
from nengo_spinnaker.builder import Model
from nengo_spinnaker.node_io import Ethernet

import nengo_spinnaker

from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.\
    nengo_application_graph_builder import NengoApplicationGraphBuilder
from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.\
    nengo_utilise_interposers import \
    NengoUtiliseInterposers
from spinnaker_graph_front_end.examples.nengo.tests.test_utilities import \
    compare_against_the_nengo_spinnaker_and_gfe_impls
from spinnaker_graph_front_end.examples.nengo.tests.examples.\
    learn_associates import create_model as la_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.\
    learn_comm_channel import create_model as lcc_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.two_d import \
    create_model as two_d_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.basic import \
    create_model as basic_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.lines import \
    create_model as lines_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.net import \
    create_model as net_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.spa import \
    create_model as spa_create_model
from spinnaker_graph_front_end.examples.nengo.tests.examples.spaun_model \
    import create_model as spaun_create_model


class TestAppGraphAndInterposerBuilder(unittest.TestCase):

    TEST_SPAUN = False

    @staticmethod
    def run_test(nengo_network, nodes_as_function_of_time,
                 nodes_as_function_of_time_time_period):

        # build via gfe nengo spinnaker
        seed = 11111
        app_graph_builder = NengoApplicationGraphBuilder()
        (app_graph, host_network, nengo_to_app_graph_map,
         random_number_generator) = app_graph_builder(
            nengo_network=nengo_network,
            machine_time_step=1.0,
            nengo_random_number_generator_seed=seed,
            decoder_cache=NoDecoderCache(),
            utilise_extra_core_for_output_types_probe=True,
            nengo_nodes_as_function_of_time=nodes_as_function_of_time,
            function_of_time_nodes_time_period=(
                nodes_as_function_of_time_time_period))
        interposer_installer = NengoUtiliseInterposers()
        app_graph = interposer_installer(
            app_graph, nengo_to_app_graph_map, random_number_generator,
            seed)

        # build via nengo - spinnaker
        nengo_spinnaker.add_spinnaker_params(nengo_network.config)
        for nengo_node in nodes_as_function_of_time:
            nengo_network.config[nengo_node].function_of_time = True
        for nengo_node in nodes_as_function_of_time_time_period:
            nengo_network.config[nengo_node].function_of_time_period = \
                nodes_as_function_of_time_time_period[nengo_node]
        io_controller = Ethernet()
        builder_kwargs = io_controller.builder_kwargs
        nengo_spinnaker_network_builder = Model()
        nengo_spinnaker_network_builder.build(nengo_network, **builder_kwargs)
        nengo_spinnaker_network_builder.add_interposers()
        nengo_operators = dict()
        nengo_operators.update(
            nengo_spinnaker_network_builder.object_operators)
        nengo_operators.update(io_controller._sdp_receivers)
        nengo_operators.update(io_controller._sdp_transmitters)

        match = compare_against_the_nengo_spinnaker_and_gfe_impls(
            nengo_operators, nengo_to_app_graph_map,
            nengo_spinnaker_network_builder.connection_map, app_graph,
            nengo_spinnaker_network_builder)

        if not match:
            raise Exception("didnt match")

    def test_application_graph_builder_learn_assocates(self):

        # build via gfe nengo spinnaker
        network, function_of_time, function_of_time_time_period = \
            la_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_learn_comm_channel(self):

        # build via gfe nengo spinnaker
        network, function_of_time, function_of_time_time_period = \
            lcc_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_example_2d(self):
        network, function_of_time, function_of_time_time_period = \
            two_d_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_basic(self):
        network, function_of_time, function_of_time_time_period = \
            basic_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_lines(self):
        network, function_of_time, function_of_time_time_period = \
            lines_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_net(self):
        network, function_of_time, function_of_time_time_period = \
            net_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_spa(self):
        network, function_of_time, function_of_time_time_period = \
            spa_create_model()
        TestAppGraphAndInterposerBuilder.run_test(
            network, function_of_time, function_of_time_time_period)

    def test_application_graph_builder_spaun_model(self):
        if self.TEST_SPAUN:
            network, function_of_time, function_of_time_time_period = \
                spaun_create_model()
            TestAppGraphAndInterposerBuilder.run_test(
                network, function_of_time, function_of_time_time_period)

if __name__ == "__main__":
    this_network, this_function_of_time, this_function_of_time_time_period = \
        la_create_model()
    TestAppGraphAndInterposerBuilder.run_test(
        this_network, this_function_of_time,
        this_function_of_time_time_period)
