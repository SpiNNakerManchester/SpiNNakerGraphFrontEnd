from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.\
    nengo_application_graph_builder import NengoApplicationGraphBuilder
from spinnaker_graph_front_end.examples.nengo.overridden_mapping_algorithms.\
    nengo_utilise_interposers import NengoUtiliseInterposers


class NengoApplicationGraphGenerator(object):

    def __init__(self):
        pass

    def __call__(
            self, nengo_network, machine_time_step,
            nengo_random_number_generator_seed, decoder_cache,
            utilise_extra_core_for_output_types_probe,
            nengo_nodes_as_function_of_time,
            function_of_time_nodes_time_period, insert_interposers):
        basic_app_graph_builder = NengoApplicationGraphBuilder()

        (nengo_operator_graph, host_network, nengo_to_app_graph_map,
         random_number_generator) = basic_app_graph_builder(
            nengo_network, machine_time_step,
            nengo_random_number_generator_seed, decoder_cache,
            utilise_extra_core_for_output_types_probe,
            nengo_nodes_as_function_of_time,
            function_of_time_nodes_time_period)

        if insert_interposers:
            interposer_insert = NengoUtiliseInterposers()
            nengo_operator_graph = interposer_insert(
                nengo_operator_graph, random_number_generator,
                nengo_random_number_generator_seed)

        return (nengo_operator_graph, host_network, nengo_to_app_graph_map,
                random_number_generator)
