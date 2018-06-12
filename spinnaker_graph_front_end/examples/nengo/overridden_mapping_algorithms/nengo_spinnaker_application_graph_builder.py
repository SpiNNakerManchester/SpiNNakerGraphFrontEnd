import nengo
import numpy
import logging

from nengo.base import NengoObject
from nengo.connection import LearningRule
from nengo.ensemble import Neurons
from nengo.processes import Process
from nengo.utils.builder import full_transform

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
    sdp_receiver_application_vertex import \
    SDPReceiverApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    sdp_transmitter_application_vertex import \
    SDPTransmitterApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_source_application_vertex import \
    ValueSourceApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    nengo_connection_application_edge import \
    NengoConnectionApplicationEdge
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    ProbeableException, NeuronTypeConstructorNotFoundException, \
    NotLocatedProbableClass
from spinnaker_graph_front_end.examples.nengo.parameters.\
    node_transmission_parameters import NodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.parameters.\
    parameter_transform import ParameterTransform
from spinnaker_graph_front_end.examples.nengo.parameters.\
    pass_through_node_transmission_parameters import \
    PassthroughNodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo import constants, \
    helpful_functions

logger = logging.getLogger(__name__)


class NengoSpiNNakerApplicationGraphBuilder(object):

    def __call__(
            self, nengo_network, extra_model_converters, machine_time_step,
            nengo_node_function_of_time, nengo_node_function_of_time_period,
            nengo_random_number_generator_seed, decoder_cache):

        # build the high level graph (operator level)

        # start by setting the specific random number generator for all seeds.
        if nengo_random_number_generator_seed is not None:
            numpy.random.seed(nengo_random_number_generator_seed)
        random_number_generator = numpy.random

        # graph for holding the nengo operators. equiv of a app graph.
        app_graph = Graph(
            allowed_vertex_types=BasicNengoApplicationVertex,
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

            # only add to the app graph if it'll run on SpiNNaker.
            if operator != nengo_node:
                app_graph.add_vertex(operator)

            # add to mapping. May point to itself if host based
            nengo_to_app_graph_map[nengo_node] = operator

        # convert connections into edges with specific data elements
        for nengo_connection in nengo_network.connections:
            edge, edge_outgoing_partition_name = self._connection_conversion(
                nengo_connection, app_graph, nengo_to_app_graph_map,
                random_number_generator, host_network, decoder_cache)
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

        return app_graph, host_network

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
            nengo_ensemble, extra_model_converters, random_number_generator):
        if nengo_ensemble.neuron_type == nengo.neurons.LIF:
            operator = LIFApplicationVertex(
                label="LIF neurons for ensemble {}".format(
                    nengo_ensemble.label),
                rng=random_number_generator,
                **LIFApplicationVertex.generate_parameters_from_ensamble(
                    nengo_ensemble, random_number_generator))
            return operator
        elif nengo_ensemble.neuron_type in extra_model_converters:
            operator = extra_model_converters[nengo_ensemble.neuron_type](
                nengo_ensemble, random_number_generator)
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
        else:  # not a function of time or a pass through node, so must be a
            # host based node, needs with wrapper, as the network assumes
            with host_network:
                if nengo_node not in host_network:
                    host_network.add(nengo_node)
            return nengo_node

    def _connection_conversion(
            self, nengo_connection, app_graph, nengo_to_app_graph_map,
            random_number_generator, host_network, decoder_cache):
        """Make a Connection and add a new signal to the Model.

        This method will build a connection and construct a new signal which
        will be included in the model.
        """
        source_vertex, source_output_port = \
            self._get_source_vertex_and_output_port(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, app_graph)

        # note that the destination input port might be a learning rule object
        destination_vertex, destination_input_port = \
            self.get_destination_vertex_and_input_port(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, app_graph)

        # build_application_edge
        if source_vertex is not None and destination_vertex is not None:
            application_edge = NengoConnectionApplicationEdge(
                pre_vertex=source_vertex, post_vertex=destination_vertex,
                rng=random_number_generator)

            # Get the transmission parameters  for the connection.
            transmission_params = self._get_transmission_parameters(
                nengo_connection, application_edge, nengo_to_app_graph_map,
                decoder_cache)

            #  reception parameters for the connection.
            reception_params = self._get_reception_parameters(nengo_connection)

            # Construct the signal parameters
            signal_params = _make_signal_parameters(source, sink, conn)

            # Add the connection to the connection map, this will automatically
            # merge connections which are equivalent.
            self.connection_map.add_connection(
                source.target.obj, source.target.port, signal_params,
                transmission_params, sink.target.obj, sink.target.port,
                reception_params
            )

    @staticmethod
    def _get_transmission_parameters_for_a_nengo_node(nengo_connection):
        # if a transmission node
        if nengo_connection.pre_obj.output is not None:

            # get size in??????
            if nengo_connection.function is None:
                size_in = nengo_connection.pre_obj.size_out
            else:
                size_in = nengo_connection.size_mid

            # return transmission parameters
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
            self, nengo_connection, application_edge, nengo_to_app_graph_map,
            decoder_cache):
        # Build the parameters object for a connection from an Ensemble.
        if nengo_connection.solver.weights:
            raise NotImplementedError(
                "SpiNNaker does not currently support neuron to neuron "
                "connections")

        # Create a random number generator
        random_number_generator = numpy.random.RandomState(
            application_edge.seed)

        # Get the transform
        transform = nengo_connection.transform

        # Solve for the decoders
        eval_points, decoders, solver_info = \
            helpful_functions.build_decoders_for_nengo_connection(
                nengo_connection, random_number_generator,
                nengo_to_app_graph_map, decoder_cache)

        application_edge.set_eval_points

        # Store the parameters in the model
        model.params[conn] = BuiltConnection(decoders=decoders,
                                             eval_points=eval_points,
                                             transform=transform,
                                             solver_info=solver_info)

        t = Transform(size_in=decoders.shape[1],
                      size_out=nengo_connection.post_obj.size_in,
                      transform=transform,
                      slice_out=nengo_connection.post_slice)
        return EnsembleTransmissionParameters(
            decoders.T, t, conn.learning_rule
        )

    def _get_transmission_parameters(
            self, nengo_connection, application_edge, nengo_to_app_graph_map,
            decoder_cache):
        # if a input node of some form. verify if its a transmission node or
        # a pass through node
        if isinstance(nengo_connection.pre_obj, nengo.Node):
            return self._get_transmission_parameters_for_a_nengo_node(
                nengo_connection)
        # if a ensemble
        elif isinstance(nengo_connection.pre_obj, nengo.Ensemble):
            return self._get_transmission_parameters_for_a_nengo_ensemble(
                nengo_connection, application_edge, nengo_to_app_graph_map,
                decoder_cache)

    @Model.reception_parameter_builders.register(nengo.base.NengoObject)
    @Model.reception_parameter_builders.register(nengo.connection.LearningRule)
    @Model.reception_parameter_builders.register(nengo.ensemble.Neurons)
    def build_generic_reception_params(model, conn):
        """Build parameters necessary for receiving packets that simulate this
        connection.
        """
        # Just extract the synapse from the connection.
        return ReceptionParameters(conn.synapse, conn.post_obj.size_in,
                                   conn.learning_rule)

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
            random_number_generator, app_graph):
        if (isinstance(nengo_to_app_graph_map[nengo_connection.pre_obj],
                       PassThroughApplicationVertex) or
                isinstance(nengo_to_app_graph_map[nengo_connection.pre_obj],
                           ValueSourceApplicationVertex)):
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
            # create new live io output operator
            operator = SDPReceiverApplicationVertex(
                label="sdp receiver app vertex for nengo node {}".format(
                    nengo_connection.pre_obj.label),
                rng=random_number_generator)

            # update records
            nengo_to_app_graph_map[nengo_connection.pre_obj] = operator
            app_graph.add_vertex(operator)

            # add to host graph for updating during vis component
            with host_network:
                if operator not in host_network:
                    host_network.add(operator)

            # return operator and the defacto output port
            return operator, constants.OUTPUT_PORT.STANDARD

    def _get_source_vertex_and_output_port(
            self, nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, app_graph):

        # if nengo object return basic operator and port
        if isinstance(nengo_connection.pre_obj, NengoObject):
            return (nengo_to_app_graph_map[nengo_connection.pre_obj],
                    constants.OUTPUT_PORT.STANDARD)
        # return result from nengo ensemble block
        elif isinstance(nengo_connection.pre_obj, nengo.Ensemble):
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
                random_number_generator, app_graph)
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

            # If connection begins at an ensemble
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
        return operator, nengo_connection.post_obj

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

            # update records
            nengo_to_app_graph_map[nengo_connection.pre_obj] = operator
            app_graph.add_vertex(operator)

            # add to host graph for updating during vis component
            with host_network:
                if operator not in host_network:
                    host_network.add(operator)

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

def _make_signal_parameters(source_spec, sink_spec, connection):
    """Create parameters for a signal using specifications provided by the
    source and sink.

    Parameters
    ----------
    source_spec : spec
        Signal specification parameters from the source of the signal.
    sink_spec : spec
        Signal specification parameters from the sink of the signal.
    connection : nengo.Connection
        The Connection for this signal

    Returns
    -------
    :py:class:`~.SignalParameters`
        Description of the signal.
    """
    # Raise an error if keyspaces are specified by the source and sink
    if source_spec.keyspace is not None and sink_spec.keyspace is not None:
        raise NotImplementedError("Cannot merge keyspaces")

    weight = max((0 or source_spec.weight,
                  0 or sink_spec.weight,
                  getattr(connection.post_obj, "size_in", 0)))

    # Create the signal parameters
    return model.SignalParameters(
        latching=source_spec.latching or sink_spec.latching,
        weight=weight,
        keyspace=source_spec.keyspace or sink_spec.keyspace,
    )