import logging

import numpy

import nengo
from nengo.base import NengoObject
from nengo.connection import LearningRule
from nengo.ensemble import Neurons
from nengo.processes import Process
from nengo.utils.builder import full_transform
from nengo.builder import connection as nengo_connection_builder
from nengo.exceptions import BuildError

from pacman.model.graphs import AbstractOutgoingEdgePartition
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import Graph
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_probeable import AbstractProbeable
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_sink_application_vertex import ValueSinkApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_outgoing_partition import ConnectionOutgoingPartition
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_input_node import NengoInputNode
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_output_node import NengoOutputNode

from spinnaker_graph_front_end.examples.nengo.utility_objects.\
    model_wrapper import ModelWrapper
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices. \
    lif_application_vertex import \
    LIFApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices. \
    pass_through_application_vertex import \
    PassThroughApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices. \
    sdp_receiver_application_vertex import \
    SDPReceiverApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices. \
    sdp_transmitter_application_vertex import \
    SDPTransmitterApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices. \
    value_source_application_vertex import \
    ValueSourceApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components. \
    connection_learning_rule_application_edge import \
    ConnectionLearningRuleApplicationEdge
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    NeuronTypeConstructorNotFoundException, NotLocatedProbableClass, \
    NotProbeableException
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    ensemble_transmission_parameters import EnsembleTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    node_transmission_parameters import NodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    pass_through_node_transmission_parameters import \
    PassthroughNodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    reception_parameters import ReceptionParameters
from spinnaker_graph_front_end.examples.nengo.utility_objects. \
    parameter_transform import ParameterTransform

logger = logging.getLogger(__name__)


class NengoApplicationGraphBuilder(object):
    """ Beast of a class, this converts between nengo objects and the 
    SpiNNaker operators that represent the nengo graph. Also produces the 
    Nengo host graph, and finally produces a map between nengo obejcts and 
    the application vertex associated with it
    
    """

    def __call__(
            self, nengo_network, extra_model_converters, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            nengo_random_number_generator_seed, decoder_cache,
            utilise_extra_core_for_decoded_output_probe):

        # build the high level graph (operator level)

        # start by setting the specific random number generator for all seeds.
        if nengo_random_number_generator_seed is not None:
            numpy.random.seed(nengo_random_number_generator_seed)
        random_number_generator = numpy.random

        # graph for holding the nengo operators. equiv of a app graph.
        app_graph = Graph(
            allowed_vertex_types=AbstractNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=constants.APP_GRAPH_NAME)

        # nengo host network, used to store nodes that do not execute on the
        # SpiNNaker machine
        host_network = nengo.Network()

        # mappings between nengo instances and the spinnaker operator graph
        nengo_to_app_graph_map = dict()

        # convert from ensembles to neuron model operators
        for nengo_ensemble in nengo_network.ensembles:
            self._ensemble_conversion(
                nengo_ensemble, extra_model_converters,
                random_number_generator,
                utilise_extra_core_for_decoded_output_probe,
                app_graph, nengo_to_app_graph_map)

        # convert from nodes to either pass through nodes or sources.
        for nengo_node in nengo_network.nodes:
            self._node_conversion(
                nengo_node, random_number_generator, machine_time_step,
                nengo_node_function_of_time,
                nengo_node_function_of_time_period,
                host_network, app_graph, nengo_to_app_graph_map)

        # convert connections into edges with specific data elements
        live_io_receivers = dict()
        for nengo_connection in nengo_network.connections:
            self._connection_conversion(
                nengo_connection, app_graph, nengo_to_app_graph_map,
                random_number_generator, host_network, decoder_cache,
                live_io_receivers)

        # for each probe, ask the operator if it supports this probe (equiv
        # of recording connection_parameters)
        for nengo_probe in nengo_network.probes:
            self._probe_conversion(
                nengo_probe, nengo_to_app_graph_map, random_number_generator,
                app_graph, host_network, decoder_cache, live_io_receivers)

        return (app_graph, host_network, nengo_to_app_graph_map,
                random_number_generator)

    def _probe_conversion(
            self, nengo_probe, nengo_to_app_graph_map, random_number_generator,
            app_graph, host_network, decoder_cache, live_io_receivers):

        # verify the app vertex it should be going to
        app_vertex = self._locate_correct_app_vertex_for_probe(
            nengo_probe, nengo_to_app_graph_map)

        # to allow some logic, flip recording to new core if requested
        # either ensemble code cant do it in dtcm, or cpu, or ITCM.
        # TODO figure out the real logic for this, as this is likely a
        # TODO major factor in the routing table compression
        if (isinstance(app_vertex, AbstractProbeable) and
                app_vertex.can_probe_variable(nengo_probe.attr)):
            app_vertex.set_probeable_variable(nengo_probe.attr)
            nengo_to_app_graph_map[nengo_probe] = app_vertex

        # if cant be recorded locally by the vertex, check if its one
        #  of those that can be recorded by a value sink vertex.
        elif nengo_probe.attr == constants.DECODER_OUTPUT_FLAG:

            # create new vertex and add to probe map.
            app_vertex = ValueSinkApplicationVertex(
                rng=random_number_generator,
                label="Sink vertex for neurons {} for probeable "
                      "attribute {}".format(app_vertex.label,
                                            nengo_probe.attr),
                size_in=nengo_probe.size_in)
            nengo_to_app_graph_map[nengo_probe] = app_vertex
            app_graph.add_vertex(app_vertex)

            # build connection and let connection conversion do rest
            with host_network:
                nengo_connection = nengo.Connection(
                    nengo_probe.target, nengo_probe,
                    synapse=nengo_probe.synapse,
                    solver=nengo_probe.solver,
                    seed=nengo_to_app_graph_map[nengo_probe].seed)
            self._connection_conversion(
                nengo_connection, app_graph, nengo_to_app_graph_map,
                random_number_generator, host_network, decoder_cache,
                live_io_receivers)
        else:
            raise NotProbeableException(
                "operator {} does not support probing {}".format(
                    app_vertex, nengo_probe.attr))

    @staticmethod
    def _locate_correct_app_vertex_for_probe(
            nengo_probe, nengo_to_app_graph_map):
        """ locates the correct app vertex for a given probe
        
        :param nengo_probe: the nengo probe
        :param nengo_to_app_graph_map: the map between nego objects and app 
        verts
        :return: the app vertex considered here
        """
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
                    target_object = nengo_probe.target.obj.ensemble
                else:
                    target_object = nengo_probe.target.ensemble

            # if the target is a learning rule, locate the ensemble at the
            # destination.
            elif isinstance(nengo_probe.target.obj,
                            nengo.connection.LearningRule):
                if isinstance(nengo_probe.target.connection.post_obj,
                              nengo.Ensemble):
                    target_object = nengo_probe.target.connection.post_obj
            else:
                raise NotLocatedProbableClass(
                    "SpiNNaker does not currently support probing '{}' on "
                    "'{}'".format(nengo_probe.attr, nengo_probe.target))
        else:
            target_object = nengo_probe.target

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
            nengo_ensemble, extra_model_converters, random_number_generator,
            utilise_extra_core_for_decoded_output_probe, app_graph,
            nengo_to_app_graph_map):
        if isinstance(nengo_ensemble.neuron_type, nengo.neurons.LIF):
            operator = LIFApplicationVertex(
                label="LIF neurons for ensemble {}".format(
                    nengo_ensemble.label),
                rng=random_number_generator,
                utilise_extra_core_for_decoded_output_probe=
                utilise_extra_core_for_decoded_output_probe,
                **LIFApplicationVertex.generate_parameters_from_ensemble(
                    nengo_ensemble, random_number_generator))
        elif nengo_ensemble.neuron_type in extra_model_converters:
            operator = extra_model_converters[nengo_ensemble.neuron_type](
                nengo_ensemble, random_number_generator)
        else:
            raise NeuronTypeConstructorNotFoundException(
                "could not find a constructor for neuron type {}. I have "
                "constructors for the following neuron types LIF,{}".format(
                    nengo_ensemble.neuron_type, extra_model_converters.keys))
        # update objects
        app_graph.add_vertex(operator)
        nengo_to_app_graph_map[nengo_ensemble] = operator

    @staticmethod
    def _node_conversion(
            nengo_node, random_number_generator, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            host_network, app_graph, nengo_to_app_graph_map):

        # ????? no idea what the size in has to do with it
        function_of_time = nengo_node.size_in == 0 and (
            not callable(nengo_node.output) or not nengo_node_function_of_time)

        if nengo_node.output is None:
            # If the Node is a pass through Node then create a new placeholder
            # for the pass through node.
            operator = PassThroughApplicationVertex(
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

            operator = ValueSourceApplicationVertex(
                label="value_source_vertex for node {}".format(
                    nengo_node.label),
                rng=random_number_generator,
                nengo_output_function=nengo_node.output,
                size_out=nengo_node.size_out,
                update_period=period)
        else:  # not a function of time or a pass through node, so must be a
            # host based node, needs with wrapper, as the network assumes
            with host_network:
                if nengo_node not in host_network:
                    host_network.add(nengo_node)
            operator = nengo_node

        # update objects
        # only add to the app graph if it'll run on SpiNNaker.
        if operator != nengo_node:
            app_graph.add_vertex(operator)

        # add to mapping. May point to itself if host based
        nengo_to_app_graph_map[nengo_node] = operator

    def _connection_conversion(
            self, nengo_connection, app_graph, nengo_to_app_graph_map,
            random_number_generator, host_network, decoder_cache,
            live_io_receivers):
        """Make a Connection and add a new signal to the Model.

        This method will build a connection and construct a new signal which
        will be included in the model.
        """
        source_vertex, source_output_port = \
            self._get_source_vertex_and_output_port(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, app_graph, live_io_receivers)

        # note that the destination input port might be a learning rule object
        destination_vertex, destination_input_port = \
            self.get_destination_vertex_and_input_port(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, app_graph)

        # build_application_edge
        if source_vertex is not None and destination_vertex is not None:

            if (destination_input_port ==
                    constants.ENSEMBLE_INPUT_PORT.LEARNING_RULE):
                application_edge = ConnectionLearningRuleApplicationEdge(
                    pre_vertex=source_vertex, post_vertex=destination_vertex,
                    learning_rule=nengo_connection.post_obj)
            else:
                application_edge = ApplicationEdge(
                    pre_vertex=source_vertex, post_vertex=destination_vertex)

            # rectify outgoing partition for data store and add to graphs
            outgoing_partition = app_graph.\
                get_outgoing_edge_partition_starting_at_vertex(
                    source_vertex, source_output_port)
            if outgoing_partition is None:
                outgoing_partition = ConnectionOutgoingPartition(
                    rng=random_number_generator, identifier=source_output_port,
                    pre_vertex=source_vertex)
                app_graph.add_outgoing_edge_partition(outgoing_partition)
            app_graph.add_edge(application_edge, source_output_port)
            nengo_to_app_graph_map[nengo_connection] = application_edge

            # Get the transmission connection_parameters  for the connection.
            transmission_params = self._get_transmission_parameters(
                nengo_connection, outgoing_partition, nengo_to_app_graph_map,
                decoder_cache)

            transmission_params, destination_input_port = transmission_params.\
                update_to_global_inhibition_if_required(destination_input_port)

            #  reception connection_parameters for the connection.
            reception_params = self._get_reception_parameters(nengo_connection)

            # Construct the signal connection_parameters
            latching_required, edge_weight = self._make_signal_parameters(
                source_vertex, destination_vertex, nengo_connection)

            # set the outgoing partition with all the channel's params
            outgoing_partition.add_all_parameters(
                transmission_params=transmission_params,
                reception_params=reception_params,
                latching_required=latching_required, weight=edge_weight,
                source_output_port=source_output_port,
                destination_input_port=destination_input_port)

    @staticmethod
    def _get_reception_parameters(nengo_connection):
        if (isinstance(nengo_connection.post_obj, nengo.base.NengoObject) or
                isinstance(nengo_connection.post_obj,
                           nengo.connection.LearningRule) or
                isinstance(nengo_connection.post_obj, nengo.ensemble.Neurons)):
            return ReceptionParameters(
                parameter_filter=nengo_connection.synapse,
                width=nengo_connection.post_obj.size_in,
                learning_rule=nengo_connection.learning_rule)

    @staticmethod
    def _get_transmission_parameters_for_a_nengo_node(nengo_connection):
        # if a transmission node
        if nengo_connection.pre_obj.output is not None:

            # get size in??????
            if nengo_connection.function is None:
                size_in = nengo_connection.pre_obj.size_out
            else:
                size_in = nengo_connection.size_mid

            # return transmission connection_parameters
            return NodeTransmissionParameters(
                transform=ParameterTransform(
                    size_in=size_in,
                    size_out=nengo_connection.post_obj.size_in,
                    transform=nengo_connection.transform,
                    slice_out=nengo_connection.post_slice),
                pre_slice=nengo_connection.pre_slice,
                parameter_function=nengo_connection.function)
        else:  # return pass through params
            return PassthroughNodeTransmissionParameters(
                transform=ParameterTransform(
                    size_in=nengo_connection.pre_obj.size_out,
                    size_out=nengo_connection.post_obj.size_in,
                    transform=nengo_connection.transform,
                    slice_in=nengo_connection.pre_slice,
                    slice_out=nengo_connection.post_slice))

    def _get_transmission_parameters_for_a_nengo_ensemble(
            self, nengo_connection, outgoing_partition, nengo_to_app_graph_map,
            decoder_cache):
        # Build the connection_parameters object for a connection from an
        # Ensemble.
        if nengo_connection.solver.weights:
            raise NotImplementedError(
                "SpiNNaker does not currently support neuron to neuron "
                "connections")

        # Create a random number generator
        random_number_generator = numpy.random.RandomState(
            outgoing_partition.seed)

        # Solve for the decoders
        decoders = self._build_decoders_for_nengo_connection(
            nengo_connection, random_number_generator, nengo_to_app_graph_map,
            decoder_cache)

        # build the parameter transformer, used during data mapping onto
        # spinnaker
        transform = ParameterTransform(
            size_in=decoders.shape[1],
            size_out=nengo_connection.post_obj.size_in,
            transform=nengo_connection.transform,
            slice_out=nengo_connection.post_slice)

        return EnsembleTransmissionParameters(
            decoders.T, transform, nengo_connection.learning_rule)

    @staticmethod
    def _build_decoders_for_nengo_connection(
            nengo_connection, random_number_generator,
            nengo_to_app_graph_map,
            decoder_cache):
        """

        :param nengo_connection: 
        :param random_number_generator: 
        :param nengo_to_app_graph_map: 
        :param decoder_cache: 
        :return: 
        """

        # fudge to support the built in enngo demanding a god object with params
        model = ModelWrapper(nengo_to_app_graph_map, decoder_cache)

        # gets encoders, gains, anf bias's from the application vertex
        encoders = nengo_to_app_graph_map[nengo_connection.pre_obj].encoders
        gain = nengo_to_app_graph_map[nengo_connection.pre_obj].gain
        bias = nengo_to_app_graph_map[nengo_connection.pre_obj].bias

        eval_points = nengo_connection_builder.get_eval_points(
            model, nengo_connection, random_number_generator)

        # TODO Figure out which version this is meant to support and use only
        # TODO that one
        try:
            targets = nengo_connection_builder.get_targets(
                model, nengo_connection, eval_points)
        except:  # yuck
            # nengo <= 2.3.0
            targets = nengo_connection_builder.get_targets(
                model, nengo_connection, eval_points)

        x = numpy.dot(eval_points, encoders.T / nengo_connection.pre_obj.radius)
        e = None
        if nengo_connection.solver.weights:
            e = nengo_to_app_graph_map[
                nengo_connection.post_obj].scaled_encoders.T[
                nengo_connection.post_slice]

            # include transform in solved weights
            targets = nengo_connection_builder.multiply(
                targets, nengo_connection.transform.T)

        try:
            wrapped_solver = model.decoder_cache.wrap_solver(
                nengo_connection_builder.solve_for_decoders)
            try:
                decoders, solver_info = wrapped_solver(
                    nengo_connection, gain, bias, x, targets,
                    rng=random_number_generator, E=e)
            except TypeError:
                # fallback for older nengo versions
                decoders, solver_info = wrapped_solver(
                    nengo_connection.solver,
                    nengo_connection.pre_obj.neuron_type,
                    gain, bias, x, targets, rng=random_number_generator, E=e)
        except BuildError:
            raise BuildError(
                "Building {}: 'activities' matrix is all zero for {}. "
                "This is because no evaluation points fall in the firing "
                "ranges of any neurons.".format(
                    nengo_connection, nengo_connection.pre_obj))

        return decoders

    def _get_transmission_parameters(
            self, nengo_connection, outgoing_partition, nengo_to_app_graph_map,
            decoder_cache):
        # if a input node of some form. verify if its a transmission node or
        # a pass through node
        if isinstance(nengo_connection.pre_obj, nengo.Node):
            return self._get_transmission_parameters_for_a_nengo_node(
                nengo_connection)
        # if a ensemble
        elif isinstance(nengo_connection.pre_obj, nengo.Ensemble):
            return self._get_transmission_parameters_for_a_nengo_ensemble(
                nengo_connection, outgoing_partition, nengo_to_app_graph_map,
                decoder_cache)

    @staticmethod
    def _get_source_vertex_and_output_port_for_nengo_ensemble(
            nengo_connection, nengo_to_app_graph_map):
        # get app operator
        operator = nengo_to_app_graph_map[nengo_connection.pre_obj]

        # if the ensemble has a learning rule. check for learnt vs standard
        if nengo_connection.learning_rule is not None:

            # If the rule modifies decoders, source it from learnt
            # output port
            if (nengo_connection.learning_rule.learning_rule_type.modifies ==
                    constants.DECODERS_FLAG):
                return operator, constants.ENSEMBLE_OUTPUT_PORT.LEARNT
        # Otherwise, it's a standard connection that can
        # be sourced from the standard output port
        return operator, constants.OUTPUT_PORT.STANDARD

    @staticmethod
    def _get_source_vertex_and_output_port_for_nengo_node(
            nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, app_graph, live_io_receivers):
        if (isinstance(nengo_to_app_graph_map[nengo_connection.pre_obj],
                       PassThroughApplicationVertex)):
            return (nengo_to_app_graph_map[nengo_connection.pre_obj],
                    constants.OUTPUT_PORT.STANDARD)
        elif (nengo_to_app_graph_map[nengo_connection.pre_obj] ==
                nengo_connection.pre_obj):
            # If this connection goes from a Node to another Node (exactly,
            # not any subclasses) then we just add both nodes and the
            # connection to the host model.
            with host_network:
                if nengo_connection.pre_obj not in host_network:
                    host_network.add(nengo_connection.pre_obj)
                if nengo_connection.post_obj not in host_network:
                    host_network.add(nengo_connection.post_obj)
                if nengo_connection not in host_network:
                    host_network.add(nengo_connection)
            return None, None
        else:
            if nengo_connection.pre_obj not in live_io_receivers:
                # create new live io output operator
                operator = SDPReceiverApplicationVertex(
                    label="sdp receiver app vertex for nengo node {}".format(
                        nengo_connection.pre_obj.label),
                    rng=random_number_generator)

                # TODO sort out this inhirtance issue.
                with host_network:
                    host_output_node = NengoOutputNode(
                        operator, nengo_connection.pre_obj.size_out)
                    if host_output_node not in host_network:
                        host_network.add(host_output_node)
                        nengo.Connection(
                            nengo_connection.pre_obj, host_output_node)

                # update records
                live_io_receivers[nengo_connection.pre_obj] = operator
                app_graph.add_vertex(operator)
            else:
                operator = live_io_receivers[nengo_connection.pre_obj]

            # return operator and the defacto output port
            return operator, constants.OUTPUT_PORT.STANDARD

    def _get_source_vertex_and_output_port(
            self, nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, app_graph, live_io_receivers):

        # return result from nengo ensemble block
        if isinstance(nengo_connection.pre_obj, nengo.Ensemble):
            return self._get_source_vertex_and_output_port_for_nengo_ensemble(
                nengo_connection, nengo_to_app_graph_map)
        # if neurons, just basic ensemble output port.
        elif isinstance(nengo_connection.pre_obj, Neurons):
            return (
                nengo_to_app_graph_map[nengo_connection.pre_obj.ensemble],
                constants.ENSEMBLE_OUTPUT_PORT.NEURONS)
        # if node, return result from node block
        elif isinstance(nengo_connection.pre_obj, nengo.Node):
            return self._get_source_vertex_and_output_port_for_nengo_node(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, app_graph, live_io_receivers)
        # if nengo object return basic operator and port
        elif isinstance(nengo_connection.pre_obj, NengoObject):
            return (nengo_to_app_graph_map[nengo_connection.pre_obj],
                    constants.OUTPUT_PORT.STANDARD)
        else:
            logger.warn("did not connect for connection starting at {}".format(
                nengo_connection.pre_obj))
            return None, None

    @staticmethod
    def _get_destination_vertex_and_input_port_for_ensemble(
            nengo_connection, nengo_to_app_graph_map):
        operator = nengo_to_app_graph_map[nengo_connection.post_obj]
        if (isinstance(nengo_connection.pre_obj, nengo.Node) and
                not callable(nengo_connection.pre_obj.output) and
                not isinstance(nengo_connection.pre_obj.output, Process) and
                nengo_connection.pre_obj.output is not None):

            # Connections from constant valued Nodes are optimised out.
            # Build the value that will be added to the direct input for the
            # ensemble.
            val = nengo_connection.pre_obj.output[
                nengo_connection.pre_slice]

            if nengo_connection.function is not None:
                val = nengo_connection.function(val)

            transform = full_transform(nengo_connection, slice_pre=False)
            operator.direct_input += numpy.dot(transform, val)
            return None, None
        else:
            # If this connection has a learning rule
            input_port = constants.INPUT_PORT.STANDARD
            if nengo_connection.learning_rule is not None:
                # If the rule modifies encoders, sink it into learnt
                # input port
                modifies = nengo_connection.learning_rule. \
                    learning_rule_type.modifies
                if modifies == constants.ENCODERS_FLAG:
                    input_port = constants.ENSEMBLE_INPUT_PORT.LEARNT
            return operator, input_port

    @staticmethod
    def _get_destination_vertex_and_input_port_for_learning_rule(
            nengo_connection, nengo_to_app_graph_map):
        # If rule modifies decoders
        operator = None
        if (nengo_connection.post_obj.learning_rule_type.modifies ==
                constants.DECODERS_FLAG):

            # If the learning rule's connection within the main connection,
            # begins at an ensemble (yuck)
            if isinstance(
                    nengo_connection.post_obj.connection.pre_obj,
                    nengo.Ensemble):

                # Sink connection into unique port on pre-synaptic
                # ensemble identified by learning rule object
                operator = nengo_to_app_graph_map[
                    nengo_connection.post_obj.connection.pre_obj]
            else:
                raise NotImplementedError(
                    "SpiNNaker only supports decoder learning "
                    "rules on connections from ensembles")
        elif (nengo_connection.post_obj.learning_rule_type.modifies ==
                constants.ENCODERS_FLAG):

            # If connections ends at an ensemble
            if isinstance(
                    nengo_connection.post_obj.connection.post_obj,
                    nengo.Ensemble):

                # Sink connection into unique port on post-synaptic
                # ensemble identified by learning rule object
                operator = nengo_to_app_graph_map[
                    nengo_connection.post_obj.connection.post_obj]
            else:
                raise NotImplementedError(
                    "SpiNNaker only supports encoder learning "
                    "rules on connections to ensembles")
        elif operator is None:
            raise NotImplementedError(
                "SpiNNaker only supports learning rules  "
                "which modify 'decoders' or 'encoders'")
        return operator, constants.ENSEMBLE_INPUT_PORT.LEARNING_RULE

    @staticmethod
    def _get_destination_vertex_and_input_port_for_nengo_node(
            nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, app_graph):
        """Get the sink for a connection terminating at a Node."""
        if isinstance(nengo_connection.post_obj, PassThroughApplicationVertex):
            return (nengo_to_app_graph_map[nengo_connection.post_obj],
                    constants.INPUT_PORT.STANDARD)
        elif (isinstance(nengo_connection.pre_obj, nengo.Node) and
                not isinstance(nengo_connection.pre_obj,
                               PassThroughApplicationVertex)):
            # If this connection goes from a Node to another Node (exactly, not
            # any subclasses) then we just add both nodes and the connection to
            # the host model.
            with host_network:
                if nengo_connection.pre_obj not in host_network:
                    host_network.add(nengo_connection.pre_obj)
                if nengo_connection.post_obj not in host_network:
                    host_network.add(nengo_connection.post_obj)
                if nengo_connection not in host_network:
                    host_network.add(nengo_connection)

            # Return None to indicate that the connection should not be
            # represented by a signal on SpiNNaker.
            return None, None
        else:
            # Otherwise we create a new InputNode for the Node at the end
            # of the given connection, then add both it and the Node to the
            # host network with a joining connection.

            # create new live io output operator
            operator = SDPTransmitterApplicationVertex(
                label="sdp transmitter app vertex for nengo node {}".format(
                    nengo_connection.pre_obj.label),
                rng=random_number_generator,
                size_in=nengo_connection.pre_obj.size_out)

            # TODO solve this inheritance issue
            host_link = NengoInputNode(operator)
            with host_network:
                if host_link not in host_network:
                    host_network.add(host_link)

            # update records
            nengo_to_app_graph_map[nengo_connection.pre_obj] = operator
            app_graph.add_vertex(operator)

            # return operator and the defacto output port
            return operator, constants.INPUT_PORT.STANDARD

    def get_destination_vertex_and_input_port(
            self, nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, app_graph):
        # if a basic nengo object, hand back a basic port
        if isinstance(nengo_connection.post_obj, NengoObject):
            return (nengo_to_app_graph_map[nengo_connection.post_obj],
                    constants.INPUT_PORT.STANDARD)
        # if neurons, hand the sink of the connection
        elif isinstance(nengo_connection.post_obj, nengo.ensemble.Neurons):
            return (nengo_to_app_graph_map[nengo_connection.post_obj.ensemble],
                    constants.ENSEMBLE_INPUT_PORT.NEURONS)
        # if ensemble, get result from ensemble block
        elif isinstance(nengo_connection.post_obj, nengo.Ensemble):
            return self._get_destination_vertex_and_input_port_for_ensemble(
                nengo_connection, nengo_to_app_graph_map)
        # if a learning rule, get result from learning rule block
        elif isinstance(nengo_connection.post_obj, LearningRule):
            return \
                self._get_destination_vertex_and_input_port_for_learning_rule(
                    nengo_connection, nengo_to_app_graph_map)
        # if a node.
        elif isinstance(nengo_connection.post_obj, nengo.Node):
            return self._get_destination_vertex_and_input_port_for_nengo_node(
                nengo_connection, nengo_to_app_graph_map,
                host_network, random_number_generator, app_graph)

    @staticmethod
    def _make_signal_parameters(
            source_vertex, destination_vertex, nengo_connection):
        """Create connection_parameters for a signal using specifications provided by the
        source and sink.
        """
        if (isinstance(destination_vertex, SDPTransmitterApplicationVertex) or
                isinstance(source_vertex, SDPTransmitterApplicationVertex)):
            return True, nengo_connection.post_obj.size_in
        else:
            return False, nengo_connection.post_obj.size_in
