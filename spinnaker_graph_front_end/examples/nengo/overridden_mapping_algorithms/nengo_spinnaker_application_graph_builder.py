import nengo
import numpy
from pacman.model.graphs import AbstractOutgoingEdgePartition
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import Graph
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    lif_application_vertex import \
    LIFApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    ProbeableException, NeuronTypeConstructorNotFoundException


class NengoSpiNNakerApplicationGraphBuilder(object):

    APP_GRAPH_NAME = "nengo_operator_graph"

    def __call__(self, nengo_network, extra_model_converters):
        app_graph = self._generate_app_graph(
            nengo_network, extra_model_converters)
        machine_graph = self._generate_machine_graph(app_graph)
        nengo_graph = self._generate_nengo_host_graph()

    def _generate_app_graph(self, nengo_network, extra_model_converters):
        random_number_generator = numpy.random

        app_graph = Graph(
            allowed_vertex_types=BasicNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=self.APP_GRAPH_NAME)
        nengo_to_app_graph_map = dict()

        for nengo_ensemble in nengo_network.ensembles:
            operator = self._ensemble_conversion(
                nengo_ensemble, extra_model_converters,
                random_number_generator)
            app_graph.add_vertex(operator)
            nengo_to_app_graph_map[nengo_ensemble] = operator

        for nengo_node in nengo_network.nodes:
            operator = self._node_conversion(
                nengo_node, random_number_generator)
            app_graph.add_vertex(operator)
            nengo_to_app_graph_map[nengo_node] = operator

        for nengo_connection in nengo_network.connections:
            edge, edge_outgoing_partition_name = self._connection_conversion(
                nengo_connection, app_graph, nengo_to_app_graph_map,
                random_number_generator)
            app_graph.add_edge(edge, edge_outgoing_partition_name)
            nengo_to_app_graph_map[nengo_connection] = edge

        # for each probe, ask the operator if it supports this probe
        for nengo_probe in nengo_network.probes:
            if nengo_probe.attr in nengo_to_app_graph_map[
                    nengo_probe.target].probeable_components:
                nengo_to_app_graph_map[
                    nengo_probe.target].set_probeable_component(
                        nengo_probe.attr)
            else:
                raise ProbeableException(
                    "the operator {}. Does not support probing of attribute"
                    " {}.".format(
                        nengo_to_app_graph_map[nengo_probe.target],
                        nengo_probe.attr))

    @staticmethod
    def _ensemble_conversion(
            nengo_ensemble, extra_model_converters, random_number_generator):
        if nengo_ensemble.neuron_type == nengo.neurons.LIF:
            operator = LIFApplicationVertex(
                label="LIF neurons for ensemble {}".format(
                    nengo_ensemble.label),
                rng=random_number_generator)
            return operator
        elif nengo_ensemble.neuron_type in extra_model_converters:
            operator = extra_model_converters[
                nengo_ensemble.neuron_type](nengo_ensemble)
            return operator
        else:
            raise NeuronTypeConstructorNotFoundException(
                "could not find a constructor for neuron type {}. I have "
                "constructors for the following neuron types LIF,{}".format(
                    nengo_ensemble.neuron_type, extra_model_converters.keys))

    def _node_conversion(self, nengo_node):


    def _connection_conversion(
            self, nengo_connection, app_graph, nengo_to_app_graph_map):




    def _generate_machine_graph(self, app_graph):


    def _generate_nengo_host_graph(self):










    def _create_host_sim(self):
        # change node_functions to reflect time
        # TODO: improve the reference simulator so that this is not needed
        #       by adding a realtime option
        node_functions = {}
        node_info = dict(start=None)
        for node in self.io_controller.host_network.all_nodes:
            if callable(node.output):
                old_func = node.output
                if node.size_in == 0:
                    def func(t, f=old_func):
                        now = time.time()
                        if node_info['start'] is None:
                            node_info['start'] = now

                        t = (now - node_info['start']) * self.timescale
                        return f(t)
                else:
                    def func(t, x, f=old_func):
                        now = time.time()
                        if node_info['start'] is None:
                            node_info['start'] = now

                        t = (now - node_info['start']) * self.timescale
                        return f(t, x)
                node.output = func
                node_functions[node] = old_func

        # Build the host simulator
        host_sim = nengo.Simulator(
            self.io_controller.host_network, dt=self.dt)
        # reset node functions
        for node, func in node_functions.items():
            node.output = func

        return host_sim