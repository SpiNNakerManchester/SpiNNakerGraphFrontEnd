import unittest

from nengo.cache import NoDecoderCache
from nengo_spinnaker.builder import Model
from nengo_spinnaker.node_io import Ethernet

from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.\
    nengo_application_graph_builder import NengoApplicationGraphBuilder
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

from spinnaker_graph_front_end.examples.nengo.tests.test_utilities import \
    compare_against_the_nengo_spinnaker_and_gfe_impls


class TestAppGraphBuilder(unittest.TestCase):

    @staticmethod
    def run_test(network):
        app_graph_builder = NengoApplicationGraphBuilder()
        (app_graph, host_network, nengo_to_app_graph_map,
         random_number_generator) = app_graph_builder(
            nengo_network=network, extra_model_converters={},
            machine_time_step=1.0,
            nengo_random_number_generator_seed=1234,
            decoder_cache=NoDecoderCache(), extra_nengo_object_parameters=None,
            utilise_extra_core_for_output_types_probe=True)

        # build via nengo - spinnaker
        io_controller = Ethernet()
        builder_kwargs = io_controller.builder_kwargs
        nengo_spinnaker_network_builder = Model()
        nengo_spinnaker_network_builder.build(network, **builder_kwargs)
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
        network = la_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_learn_comm_channel(self):

        # build via gfe nengo spinnaker
        network = lcc_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_example_2d(self):
        network = two_d_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_basic(self):
        network = basic_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_lines(self):
        network = lines_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_net(self):
        network = net_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_spa(self):
        network = spa_create_model()
        TestAppGraphBuilder.run_test(network)

    def test_application_graph_builder_spaun_model(self):
        network = spaun_create_model()
        TestAppGraphBuilder.run_test(network)

if __name__ == "__main__":
    network = la_create_model()
    TestAppGraphBuilder.run_test(network)
