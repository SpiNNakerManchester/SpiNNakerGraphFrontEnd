import nengo
import numpy

from nengo.processes import Process
from pacman.model.graphs import AbstractOutgoingEdgePartition
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import Graph
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    lif_application_vertex import \
    LIFApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    pass_through_application_vertex import \
    PassThroughApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_source_application_vertex import \
    ValueSourceApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    ProbeableException, NeuronTypeConstructorNotFoundException, \
    NotLocatedProbableClass


class NengoSpiNNakerApplicationGraphBuilder(object):

    APP_GRAPH_NAME = "nengo_operator_graph"

    def __call__(
            self, nengo_network, extra_model_converters, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            nengo_random_number_generator_seed):

        # build the high level graph (operator level)
        app_graph, host_network = self._generate_app_graph(
            nengo_network, extra_model_converters, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            nengo_random_number_generator_seed)

        # build the spinnaker machine graph
        machine_graph = self._generate_machine_graph(app_graph)

        # build the nengo host graph used for vis
        nengo_graph = self._generate_nengo_host_graph()

        # return the 3 graphs
        return app_graph, machine_graph, nengo_graph

    def _generate_app_graph(
            self, nengo_network, extra_model_converters, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            nengo_random_number_generator_seed):

        # specific random number generator for all seeds.
        if nengo_random_number_generator_seed is not None:
            numpy.random.seed(nengo_random_number_generator_seed)
        random_number_generator = numpy.random

        # graph for holding the nengo operators. equiv of a app graph.
        app_graph = Graph(
            allowed_vertex_types=BasicNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=self.APP_GRAPH_NAME)

        # nengo host network, used to store nodes that do not execute on the
        # SpiNNaker machine
        host_network = nengo.Network()

        # mappings between nengo instances and the spinnaker operator graph
        nengo_to_app_graph_map = dict()

        # convert from ensembles to neuron model operators
        for nengo_ensemble in nengo_network.ensembles:
            operator = self._ensemble_conversion(
                nengo_ensemble, extra_model_converters,
                random_number_generator)
            app_graph.add_vertex(operator)
            nengo_to_app_graph_map[nengo_ensemble] = operator

        # convert from nodes to either pass through nodes or sources.
        for nengo_node in nengo_network.nodes:
            operator = self._node_conversion(
                nengo_node, random_number_generator, machine_time_step,
                nengo_node_function_of_time,
                nengo_node_function_of_time_period,
                host_network)
            app_graph.add_vertex(operator)
            nengo_to_app_graph_map[nengo_node] = operator

        # convert connections into edges with specific data elements
        for nengo_connection in nengo_network.connections:
            edge, edge_outgoing_partition_name = self._connection_conversion(
                nengo_connection, app_graph, nengo_to_app_graph_map,
                random_number_generator)
            app_graph.add_edge(edge, edge_outgoing_partition_name)
            nengo_to_app_graph_map[nengo_connection] = edge

        # for each probe, ask the operator if it supports this probe (equiv
        # of recording parameters)
        for nengo_probe in nengo_network.probes:
            if nengo_probe.attr in nengo_to_app_graph_map[
                    nengo_probe.target].probeable_components:

                # verify the app vertex it should be going to
                app_vertex = self._locate_correct_app_vertex_for_probe(
                    nengo_probe, nengo_to_app_graph_map)
                app_vertex.set_probeable_component(nengo_probe.attr)
            else:
                raise ProbeableException(
                    "the operator {}. Does not support probing of attribute"
                    " {}.".format(
                        nengo_to_app_graph_map[nengo_probe.target],
                        nengo_probe.attr))

    @staticmethod
    def _locate_correct_app_vertex_for_probe(
            nengo_probe, nengo_to_app_graph_map):
        target_object = None
        # ensure the target is of a nengo object
        if isinstance(nengo_probe.target, nengo.base.ObjView):

            # if the target is an ensemble, get the ensemble's app vert
            if isinstance(nengo_probe.target.obj, nengo.Ensemble):
                target_object = nengo_probe.target.obj

            # if the target is a Neurons from an ensemble, backtrack to the
            # ensemble
            elif isinstance(nengo_probe.target.obj, nengo.ensemble.Neurons):
                if isinstance(nengo_probe.target, nengo.base.ObjView):
                    target_object =  nengo_probe.target.obj.ensemble
                else:
                    target_object = nengo_probe.target.ensemble

            # if the target is a learning rule, locate the ensemble at the
            # destination.
            elif  isinstance(nengo_probe.target.obj,
                             nengo.connection.LearningRule):
                if isinstance(nengo_probe.target.connection.post_obj,
                              nengo.Ensemble):
                    target_object = nengo_probe.target.connection.post_obj
        else:
            target_object =  nengo_probe.target

        # if the target object has been found, return the app vertex
        # associated with it. else raise exception
        if target_object is not None:
            return nengo_to_app_graph_map[target_object]
        else:
            raise NotLocatedProbableClass(
                "SpiNNaker does not currently support probing '{}' on "
                "'{}'".format(nengo_probe.attr, nengo_probe.target))

    @staticmethod
    def _ensemble_conversion(
            nengo_ensemble, extra_model_converters, random_number_generator):
        if nengo_ensemble.neuron_type == nengo.neurons.LIF:
            operator = LIFApplicationVertex(
                label="LIF neurons for ensemble {}".format(
                    nengo_ensemble.label),
                rng=random_number_generator,
                params=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX)
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

    @staticmethod
    def _node_conversion(
            nengo_node, random_number_generator, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            host_network):

        # ????? no idea what the size in has to do with it
        function_of_time = nengo_node.size_in == 0 and (
            not callable(nengo_node.output) or not nengo_node_function_of_time)

        if nengo_node.output is None:
            # If the Node is a pass through Node then create a new placeholder
            # for the pass through node.
            return PassThroughApplicationVertex(
                label=nengo_node.label, rng=random_number_generator)

        elif function_of_time:
            # If the Node is a function of time then add a new value source for
            # it.  Determine the period by looking in the config, if the output
            # is a constant then the period is dt (i.e., it repeats every
            # time step).
            if callable(nengo_node.output) or isinstance(
                    nengo_node.output, Process):

                period = nengo_node_function_of_time_period
            else:
                period = machine_time_step

            return ValueSourceApplicationVertex(
                label="value_source_vertex for node {}".format(
                    nengo_node.label),
                rng=random_number_generator,
                nengo_node_output=nengo_node.output,
                nengo_node_size_out=nengo_node.size_out,
                period=period)
        else: # not a function of time or a pass through node, so must be a
            # host based node
            host_network.add(nengo_node)

    def _connection_conversion(
            self, nengo_connection, app_graph, nengo_to_app_graph_map,
            random_number_generator):




    def _generate_machine_graph(self, app_graph):


    def _generate_nengo_host_graph(self):










    def _create_host_sim(self, host_network):
        # change node_functions to reflect time
        # TODO: improve the reference simulator so that this is not needed
        #       by adding a realtime option
        node_functions = {}
        node_info = dict(start=None)
        for node in host_network.all_nodes:
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