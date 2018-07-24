import logging
from collections import defaultdict

import numpy

import nengo
from nengo.base import NengoObject
from nengo.connection import LearningRule
from nengo.ensemble import Neurons
from nengo.processes import Process
from nengo.utils.builder import full_transform
from nengo.builder import connection as nengo_connection_builder, Signal
from nengo.exceptions import BuildError

from pacman.model.graphs import AbstractOutgoingEdgePartition
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import Graph
from spinn_utilities.log import FormatAdapter
from spinnaker_graph_front_end.examples.nengo import constants, \
    helpful_functions
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_object import AbstractNengoObject
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_probeable import AbstractProbeable
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_sink_application_vertex import ValueSinkApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_application_edge import ConnectionApplicationEdge
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_outgoing_partition import ConnectionOutgoingPartition
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    partition_identifier import PartitionIdentifier
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
from spinnaker_graph_front_end.examples.nengo.utility_objects.\
    parameter_extraction_from_nengo_ensamble import \
    ParameterExtractionFromNengoEnsemble
from spinnaker_graph_front_end.examples.nengo.utility_objects. \
    parameter_transform import ParameterTransform

logger = FormatAdapter(logging.getLogger(__name__))


class NengoApplicationGraphBuilder(object):
    """ Beast of a class, this converts between nengo objects and the 
    SpiNNaker operators that represent the nengo graph. Also produces the 
    Nengo host graph, and finally produces a map between nengo objects and 
    the application vertex associated with it
    
    """

    def __call__(
            self, nengo_network, machine_time_step,
            nengo_random_number_generator_seed, decoder_cache,
            utilise_extra_core_for_probes,
            nengo_nodes_as_function_of_time,
            function_of_time_nodes_time_period):
        """ entrance method to start converting from nengo objects to nengo 
        operator graph (spinnaker app graph, including pass through nodes). 
        
        :param nengo_network: the nengo network 
        :param utilise_extra_core_for_probes: flag that allows \
        the user to decide if probes should be on separate vertices or not.
        :param machine_time_step: the machine time step 
        :param nengo_nodes_as_function_of_time: set of nodes which will \
        operate as function of times.
        :param decoder_cache: still don't know what this is for yet.
        :param nengo_random_number_generator_seed: The nengo random number \
        generator seed.
        :param function_of_time_nodes_time_period: the dict of nodes to function
        :param nengo_random_number_generator_seed: The seed for the random \
        number generator for the nengo objects. 
        :return: 4 things in a tuple. \
        1. the nengo operator graph (an application graph with pass through \
        nodes.\
        2. The network of vertices which will be updated on host.\
        3. the mapping between nengo object and a nengo operator. \
        4. the random number generator for the nengo simulation.
        :rtype: tuple of (\
            ApplicationGraph, nengoNetwork,\
            Dict[NengoObject]->ApplicationVertex, int)
        """

        # start by setting the specific random number generator for all seeds.
        if nengo_random_number_generator_seed is not None:
            numpy.random.seed(nengo_random_number_generator_seed)
        random_number_generator = numpy.random

        # graph for holding the nengo operators. equiv of a app graph.
        nengo_operator_graph = Graph(
            allowed_vertex_types=AbstractNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=constants.APP_GRAPH_NAME)

        # nengo host network, used to store nodes that do not execute on the
        # SpiNNaker machine
        host_network = nengo.Network()

        # mappings between nengo instances and the spinnaker operator graph
        nengo_to_app_graph_map = dict()

        self._build_sub_network_graph(
            nengo_network, random_number_generator,
            utilise_extra_core_for_probes, nengo_operator_graph,
            nengo_to_app_graph_map, machine_time_step, host_network,
            nengo_nodes_as_function_of_time, decoder_cache,
            nengo_random_number_generator_seed,
            function_of_time_nodes_time_period)

        return (nengo_operator_graph, host_network, nengo_to_app_graph_map,
                random_number_generator)

    def _build_sub_network_graph(
            self, nengo_network, random_number_generator,
            utilise_extra_core_for_output_types_probe,
            nengo_operator_graph, nengo_to_app_graph_map, machine_time_step,
            host_network, nengo_nodes_as_function_of_time, decoder_cache,
            nengo_random_number_generator_seed,
            function_of_time_nodes_time_period):
        """ Builds an entire sub network from the nengo network. 
        
        :param nengo_network: the nengo network 
        :param random_number_generator: the nengo network random number \
        generator
        :param utilise_extra_core_for_output_types_probe: flag that allows \
        the user to decide if probes should be on separate vertices or not.
        :param nengo_operator_graph: the nengo operator graph (a type of \
        application graph)
        :param nengo_to_app_graph_map: the map between nengo and nengo \
        operators.
        :param machine_time_step: the machine time step 
        :param host_network: the collection of nodes to be simulated on host.
        :param nengo_nodes_as_function_of_time: set of nodes which will \
        operate as function of times.
        :param decoder_cache: still don't know what this is for yet.
        :param nengo_random_number_generator_seed: The nengo random number \
        generator seed.
        :param function_of_time_nodes_time_period: the dict of nodes to function
        :return: 4 things in a tuple. \
        1. the nengo operator graph (an application graph with pass through \
        nodes.\
        2. The network of vertices which will be updated on host.\
        3. the mapping between nengo object and a nengo operator. \
        4. the random number generator for the nengo simulation.
        :rtype: tuple of (\
            ApplicationGraph, nengoNetwork,\
            Dict[NengoObject]->ApplicationVertex, int)
        """

        for nengo_sub_network in nengo_network.networks:
            self._build_sub_network_graph(
                nengo_sub_network, random_number_generator,
                utilise_extra_core_for_output_types_probe,
                nengo_operator_graph, nengo_to_app_graph_map, machine_time_step,
                host_network, nengo_nodes_as_function_of_time, decoder_cache,
                nengo_random_number_generator_seed,
                function_of_time_nodes_time_period)

        # convert from ensembles to neuron model operators
        for nengo_ensemble in nengo_network.ensembles:
            self._ensemble_conversion(
                nengo_ensemble, random_number_generator,
                utilise_extra_core_for_output_types_probe,
                nengo_operator_graph, nengo_to_app_graph_map)

        # convert from nodes to either pass through nodes or sources.
        for nengo_node in nengo_network.nodes:
            self._node_conversion(
                nengo_node, random_number_generator, machine_time_step,
                host_network, nengo_operator_graph, nengo_to_app_graph_map,
                utilise_extra_core_for_output_types_probe,
                nengo_nodes_as_function_of_time,
                function_of_time_nodes_time_period)

        # convert connections into edges with specific data elements
        live_io_receivers = dict()
        live_io_senders = dict()
        for nengo_connection in nengo_network.connections:
            self._connection_conversion(
                nengo_connection, nengo_operator_graph, nengo_to_app_graph_map,
                random_number_generator, host_network, decoder_cache,
                live_io_receivers, live_io_senders)

        # for each probe, ask the operator if it supports this probe (equiv
        # of recording connection_parameters)
        for nengo_probe in nengo_network.probes:
            self._probe_conversion(
                nengo_probe, nengo_to_app_graph_map, random_number_generator,
                nengo_operator_graph, host_network, decoder_cache,
                live_io_receivers, nengo_random_number_generator_seed,
                live_io_senders)

        return (nengo_operator_graph, host_network, nengo_to_app_graph_map,
                random_number_generator)

    def _probe_conversion(
            self, nengo_probe, nengo_to_app_graph_map, random_number_generator,
            nengo_operator_graph, host_network, decoder_cache,
            live_io_receivers, nengo_random_number_generator_seed,
            live_io_senders):
        """ converts a nengo probe into a nengo operator 
        
        :param nengo_probe: the nengo probe in question
        :param nengo_to_app_graph_map: the nengo to nengo operator map
        :param random_number_generator: the simulator random number generator.
        :param nengo_operator_graph: the nengo operator graph
        :param host_network: the collection of nodes to be ran on the host \
        machine
        :param decoder_cache: still don't know what this is for yet.
        :param live_io_senders: dict of nengo object to sdp transmitters 
        :param nengo_random_number_generator_seed: the seed for the nengo \
        random number generator
        :param live_io_receivers: dict of nengo object to sdp receivers 
        :rtype: None: 
        """

        # verify the app vertex it should be going to
        app_vertex = self._locate_correct_app_vertex_for_probe(
            nengo_probe, nengo_to_app_graph_map)

        if isinstance(app_vertex, PassThroughApplicationVertex):
            operator = ValueSinkApplicationVertex(
                label="value sink for probe {}".format(nengo_probe.label),
                rng=random_number_generator, size_in=nengo_probe.size_in,
                seed=helpful_functions.get_seed(nengo_probe))
            nengo_operator_graph.add_vertex(operator)
            nengo_to_app_graph_map[nengo_probe] = operator

            # NOTE: the add_to_container=False is needed, else its built into
            #  the network. which we don't want here
            nengo_connection = nengo.Connection(
                nengo_probe.target, nengo_probe,
                synapse=nengo_probe.synapse,
                seed=nengo_random_number_generator_seed,
                add_to_container=False)

            self._connection_conversion(
                nengo_connection, nengo_operator_graph,
                nengo_to_app_graph_map, random_number_generator,
                host_network, decoder_cache, live_io_receivers,
                live_io_senders)
        else:
            # to allow some logic, flip recording to new core if requested
            # either ensemble code cant do it in DTCM, or cpu, or ITCM.
            # TODO figure out the real logic for this, as this is likely a
            # TODO major factor in the routing table compression
            if (isinstance(app_vertex, AbstractProbeable) and
                    app_vertex.can_probe_variable(nengo_probe.attr)):
                app_vertex.set_probeable_variable(nengo_probe.attr)
                nengo_to_app_graph_map[nengo_probe] = app_vertex

            # if cant be recorded locally by the vertex, check if its one
            #  of those that can be recorded by a value sink vertex.
            elif (nengo_probe.attr == constants.DECODER_OUTPUT_FLAG or
                  nengo_probe.attr == constants.RECORD_OUTPUT_FLAG):

                # create new vertex and add to probe map.
                app_vertex = ValueSinkApplicationVertex(
                    rng=random_number_generator,
                    label="Sink vertex for neurons {} for probeable "
                          "attribute {}".format(nengo_probe.label,
                                                nengo_probe.attr),
                    size_in=nengo_probe.size_in,
                    seed=helpful_functions.get_seed(nengo_probe))
                nengo_to_app_graph_map[nengo_probe] = app_vertex
                nengo_operator_graph.add_vertex(app_vertex)

                # build connection and let connection conversion do rest
                with host_network:
                    nengo_connection = nengo.Connection(
                        nengo_probe.target, nengo_probe,
                        synapse=nengo_probe.synapse,
                        solver=nengo_probe.solver,
                        seed=nengo_to_app_graph_map[nengo_probe].seed,
                        add_to_container=False)
                self._connection_conversion(
                    nengo_connection, nengo_operator_graph,
                    nengo_to_app_graph_map, random_number_generator,
                    host_network, decoder_cache, live_io_receivers,
                    live_io_senders)
            else:
                raise NotProbeableException(
                    "operator {} does not support probing {}".format(
                        app_vertex, nengo_probe.attr))

    @staticmethod
    def _locate_correct_app_vertex_for_probe(
            nengo_probe, nengo_to_app_graph_map):
        """ locates the correct app vertex for a given probe
        
        :param nengo_probe: the nengo probe
        :param nengo_to_app_graph_map: the map between nengo objects and 
        nengo operator graph 
        :return: the nengo operator considered here
        """

        # ensure the target is of a nengo object
        target = nengo_probe.target
        if isinstance(nengo_probe.target, nengo.base.ObjView):
            target = target.obj

        # if the target is a Node
        if isinstance(target, nengo.Node):
            target_object = nengo_probe.target

        # if the target is an ensemble, get the ensemble's app vertex
        elif isinstance(target, nengo.Ensemble):
            target_object = target

        # if the target is a Neurons from an ensemble, backtrack to the
        # ensemble
        elif isinstance(target, nengo.ensemble.Neurons):
            if isinstance(nengo_probe.target, nengo.base.ObjView):
                target_object = nengo_probe.target.obj.ensemble
            else:
                target_object = nengo_probe.target.ensemble

        # if the target is a learning rule, locate the ensemble at the
        # destination.
        elif isinstance(target, nengo.connection.LearningRule):
            if isinstance(nengo_probe.target.connection.post_obj,
                          nengo.Ensemble):
                target_object = nengo_probe.target.connection.post_obj
            else:
                raise NotLocatedProbableClass(
                    "SpiNNaker does not currently support probing '{}' on "
                    "'{}'".format(
                        nengo_probe.attr, nengo_probe.target.
                        learning_rule_type.__class__.__name__))
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
            nengo_ensemble, random_number_generator,
            utilise_extra_core_for_output_types_probe, nengo_operator_graph,
            nengo_to_app_graph_map):
        """  This converts a nengo ensemble into a nengo operator used in the \
        nengo operator graph. 
        
        :param nengo_ensemble: the nengo ensemble to be converted
        :param random_number_generator: the random number generator of the \
        simulator.
        :param nengo_operator_graph: the application graph holding nengo \
        operators.
        :param nengo_to_app_graph_map: map between nengo object and nengo \
        operators.
        :param utilise_extra_core_for_output_types_probe: flag that allows \
        the user to decide if probes should be on separate vertices or not.
        :rtype: None
        """
        if isinstance(nengo_ensemble.neuron_type, nengo.neurons.LIF):
            params_from_nengo_ensemble = \
                ParameterExtractionFromNengoEnsemble(
                    nengo_ensemble, random_number_generator)
            operator = LIFApplicationVertex(
                label="LIF neurons for ensemble {}".format(
                    nengo_ensemble.label),
                rng=random_number_generator,
                size_in=nengo_ensemble.size_in,
                seed=helpful_functions.get_seed(nengo_ensemble),
                utilise_extra_core_for_output_types_probe=(
                    utilise_extra_core_for_output_types_probe),
                eval_points=params_from_nengo_ensemble.eval_points,
                encoders=params_from_nengo_ensemble.encoders,
                scaled_encoders=params_from_nengo_ensemble.scaled_encoders,
                max_rates=params_from_nengo_ensemble.max_rates,
                intercepts=params_from_nengo_ensemble.intercepts,
                gain=params_from_nengo_ensemble.gain,
                bias=params_from_nengo_ensemble.bias)
        else:
            raise NeuronTypeConstructorNotFoundException(
                "could not find a constructor for neuron type {}. I have "
                "constructors for the following neuron types LIF".format(
                    nengo_ensemble.neuron_type))
        # update objects
        nengo_operator_graph.add_vertex(operator)
        nengo_to_app_graph_map[nengo_ensemble] = operator

    @staticmethod
    def _node_conversion(
            nengo_node, random_number_generator, machine_time_step,
            host_network, nengo_operator_graph, nengo_to_app_graph_map,
            utilise_extra_core_for_output_types_probe,
            nengo_nodes_as_function_of_time,
            function_of_time_nodes_time_period):
        """ This converts a nengo node into a nengo operator used in the \
        nengo operator graph. 
        
        :param nengo_node: the nengo node to be converted
        :param random_number_generator: the random number generator of the \
        simulator.
        :param machine_time_step: the machine time step of the simulation.
        :param host_network: the holder for nengo nodes to be executed on host.
        :param nengo_operator_graph: the application graph holding nengo \
        operators.
        :param nengo_to_app_graph_map: map between nengo object and nengo \
        operators.
        :param utilise_extra_core_for_output_types_probe: flag that allows \
        the user to decide if probes should be on separate vertices or not.
        :param nengo_nodes_as_function_of_time: store of nodes which should \
        be a function of time.
        :param function_of_time_nodes_time_period: store of nodes which have \
        a function of time time period. 
        :rtype: None
        """

        # effects if the spike source repeats every time step
        function_of_time = nengo_node.size_in == 0 and (
            not callable(nengo_node.output) or
            nengo_node in nengo_nodes_as_function_of_time)

        if nengo_node.output is None:
            # If the Node is a pass through Node then create a new placeholder
            # for the pass through node.
            operator = PassThroughApplicationVertex(
                label=nengo_node.label, rng=random_number_generator,
                seed=helpful_functions.get_seed(nengo_node))

        elif function_of_time:
            # If the Node is a function of time then add a new value source for
            # it.  Determine the period by looking in the config, if the output
            # is a constant then the period is dt (i.e., it repeats every
            # time step).
            if callable(nengo_node.output) or isinstance(
                    nengo_node.output, Process):
                if nengo_node in function_of_time_nodes_time_period:
                    period = function_of_time_nodes_time_period[nengo_node]
                else:
                    logger.warning(
                        "The {} parameter has not been provided. Please "
                        "provide it for the node {} with label {} within the "
                        "extra_object_params parameter. Will use None "
                        "instead".format(
                            constants.FUNCTION_OF_TIME_PERIOD_PARAM_FLAG,
                            nengo_node, nengo_node.label))
                    period = None
            else:
                period = (machine_time_step /
                          constants.CONVERT_MILLISECONDS_TO_SECONDS)

            operator = ValueSourceApplicationVertex(
                label="value_source_vertex for node {}".format(
                    nengo_node.label),
                rng=random_number_generator,
                nengo_output_function=nengo_node.output,
                size_out=nengo_node.size_out,
                update_period=period, 
                utilise_extra_core_for_output_types_probe=(
                    utilise_extra_core_for_output_types_probe),
                seed=helpful_functions.get_seed(nengo_node))
        else:  # not a function of time or a pass through node, so must be a
            # host based node, needs with wrapper, as the network assumes
            with host_network:
                if nengo_node not in host_network:
                    host_network.add(nengo_node)
            operator = None

        # update objects
        # only add to the app graph if it'll run on SpiNNaker.
        if operator is not None and operator != nengo_node:
            nengo_operator_graph.add_vertex(operator)

        # add to mapping. May point to itself if host based
        nengo_to_app_graph_map[nengo_node] = operator

    def _connection_conversion(
            self, nengo_connection, nengo_operator_graph,
            nengo_to_app_graph_map, random_number_generator, host_network,
            decoder_cache, live_io_receivers, live_io_senders):
        """Make a Connection and add a new signal to the Model.

        This method will build a connection and construct a new signal which
        will be included in the model.
        
        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param host_network: the vertices and edges which will be simulated \
        on host machine.
        :param random_number_generator: the random number generator used by \
        the nengo objects
        :param nengo_operator_graph: the nengo operator graph. 
        :param live_io_senders: dict of nengo object to sdp transmitters 
        :param decoder_cache: still don't know what this is for yet.
        :param random_number_generator: the nengo simulator random number \
        generator
        :param live_io_receivers: dict of nengo object to sdp receivers 
        :rtype: None
        """

        source_vertex, source_output_port = \
            self._get_source_vertex_and_output_port(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, nengo_operator_graph,
                live_io_receivers)

        # note that the destination input port might be a learning rule object
        destination_vertex, destination_input_port = \
            self.get_destination_vertex_and_input_port(
                nengo_connection, nengo_to_app_graph_map, host_network,
                random_number_generator, nengo_operator_graph, live_io_senders)

        # build_application_edge
        if source_vertex is not None and destination_vertex is not None:

            # Construct the signal connection_parameters
            latching_required, edge_weight = self._make_signal_parameter(
                source_vertex, destination_vertex, nengo_connection)

            # Get the transmission connection_parameters  for the connection.
            transmission_parameter = self._get_transmission_parameters(
                nengo_connection,
                AbstractNengoObject.get_seed(random_number_generator),
                nengo_to_app_graph_map, decoder_cache)

            # Swap out the connection for a global inhibition connection if
            # possible.
            if transmission_parameter is not None:
                transmission_parameter, destination_input_port = \
                    transmission_parameter.\
                    update_to_global_inhibition_if_required(
                        destination_input_port)

            #  reception connection_parameters for the connection.
            reception_params = self._get_reception_parameters(nengo_connection)

            application_edge = ConnectionApplicationEdge(
                pre_vertex=source_vertex, post_vertex=destination_vertex,
                input_port=destination_input_port,
                reception_parameters=reception_params)

            # rectify outgoing partition for data store and add to graphs
            identifier = PartitionIdentifier(
                source_output_port, transmission_parameter, edge_weight,
                latching_required)
            outgoing_partition = nengo_operator_graph.\
                get_outgoing_edge_partition_starting_at_vertex(
                    source_vertex, identifier)
            if outgoing_partition is None:
                outgoing_partition = ConnectionOutgoingPartition(
                    rng=random_number_generator,
                    seed=helpful_functions.get_seed(nengo_connection),
                    identifier=identifier, pre_vertex=source_vertex)
                nengo_operator_graph.add_outgoing_edge_partition(
                    outgoing_partition)
            nengo_operator_graph.add_edge(application_edge, identifier)
            nengo_to_app_graph_map[nengo_connection] = application_edge

    @staticmethod
    def _get_reception_parameters(nengo_connection):
        """ returns the reception parameters of the nengo connection
        
        :param nengo_connection: the nengo connection in question
        :return: the reception parameters
        :rtype: ReceptionParameters
        """
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
        """acquire the parameters for transmitting down the nengo connection \ 
        an node  
        
        :param nengo_connection: the nengo connection in question
        :return: the transmission parameters for this nengo connection
        :rtype: NodeTransmissionParameters or \
        PassthroughNodeTransmissionParameters
        """
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
            self, nengo_connection, partition_seed, nengo_to_app_graph_map,
            decoder_cache):
        """ acquire the parameters for transmitting down the nengo connection \ 
        an ensemble      
        :param nengo_connection: the nengo connection in question
        :param partition_seed: the seed for the outgoing edge partition
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param decoder_cache: still don't know what this is for yet.
        :return: the transmission parameters for this nengo connection
        :rtype: EnsembleTransmissionParameters
        """
        # Build the connection_parameters object for a connection from an
        # Ensemble.
        if nengo_connection.solver.weights:
            raise NotImplementedError(
                "SpiNNaker does not currently support neuron to neuron "
                "connections")

        # Create a random number generator
        random_number_generator = numpy.random.RandomState(partition_seed)

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
            nengo_connection, random_number_generator, nengo_to_app_graph_map,
            decoder_cache):
        """ builds decoders for the nengo connection

        :param nengo_connection: the nengo connection in question
        :param random_number_generator: the random number generator for the \
        simulation.
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param decoder_cache: still don't know what this is for yet.
        :return: the decoders ???????
        """

        # fudge to support the built in nengo demanding a god object with params
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
            self, nengo_connection, partition_seed, nengo_to_app_graph_map,
            decoder_cache):
        """ acquire the parameters for transmitting down the nengo connection
        
        :param nengo_connection: the nengo connection in question
        :param partition_seed: the seed for the outgoing edge partition
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param decoder_cache: still don't know what this is for yet.
        :return: The transmission parameters or None
        """
        # if a input node of some form. verify if its a transmission node or
        # a pass through node
        if isinstance(nengo_connection.pre_obj, nengo.Node):
            return self._get_transmission_parameters_for_a_nengo_node(
                nengo_connection)
        # if a ensemble
        elif isinstance(nengo_connection.pre_obj, nengo.Ensemble):
            return self._get_transmission_parameters_for_a_nengo_ensemble(
                nengo_connection, partition_seed, nengo_to_app_graph_map,
                decoder_cache)
        elif isinstance(nengo_connection.pre_obj, nengo.ensemble.Neurons):
            return None
        else:
            raise Exception("not recognised connection pre object {}.".format(
                nengo_connection.pre_obj))

    @staticmethod
    def _get_source_vertex_and_output_port_for_nengo_ensemble(
            nengo_connection, nengo_to_app_graph_map):
        """ locate the source vertex and output port from that source vertex \
        for a given nengo connection that starts at a nengo ensemble
        
        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :return: app vertex, and a output port enum 
        """
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
            random_number_generator, nengo_operator_graph, live_io_receivers):
        """ locate the source vertex and output port from that source vertex \
        for a given nengo connection that starts at a nengo node

        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param host_network: the vertices and edges which will be simulated \
        on host machine.
        :param random_number_generator: the random number generator used by \
        the nengo objects
        :param nengo_operator_graph: the nengo operator graph. 
        :param live_io_receivers: dict of nengo object to sdp receivers 
        :return: app vertex, and a output port enum 
        """
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
            if nengo_connection.pre_obj not in live_io_receivers:
                # create new live io output operator
                operator = SDPReceiverApplicationVertex(
                    label="sdp receiver app vertex for nengo node {}".format(
                        nengo_connection.pre_obj.label),
                    rng=random_number_generator,
                    size_in=nengo_connection.pre_obj.size_out,
                    seed=helpful_functions.get_seed(nengo_connection.pre_obj))

                # TODO sort out this inhirtance issue.
                with host_network:
                    host_output_node = NengoOutputNode(operator)
                    if host_output_node not in host_network:
                        host_network.add(host_output_node)
                        nengo.Connection(
                            nengo_connection.pre_obj, host_output_node)

                # update records
                live_io_receivers[nengo_connection.pre_obj] = operator
                if (nengo_connection.pre_obj in nengo_to_app_graph_map and
                        nengo_to_app_graph_map[nengo_connection.pre_obj] is not
                        None):
                    raise Exception("ah")

                nengo_to_app_graph_map[nengo_connection.pre_obj] = operator
                nengo_operator_graph.add_vertex(operator)
            else:
                operator = live_io_receivers[nengo_connection.pre_obj]

            # return operator and the defacto output port
            return operator, constants.OUTPUT_PORT.STANDARD

    def _get_source_vertex_and_output_port(
            self, nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, nengo_operator_graph, live_io_receivers):
        """ locate the source vertex and output port from that source vertex \
        for a given nengo connection

        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param host_network: the vertices and edges which will be simulated \
        on host machine.
        :param random_number_generator: the random number generator used by \
        the nengo objects
        :param nengo_operator_graph: the nengo operator graph. 
        :param live_io_receivers: dict of nengo object to sdp receivers 
        :return: app vertex, and a output port enum 
        """

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
                random_number_generator, nengo_operator_graph,
                live_io_receivers)
        # if nengo object return basic operator and port
        elif isinstance(nengo_connection.pre_obj, NengoObject):
            return (nengo_to_app_graph_map[nengo_connection.pre_obj],
                    constants.OUTPUT_PORT.STANDARD)
        else:
            logger.warning(
                "did not connect for connection starting at {}".format(
                    nengo_connection.pre_obj))
            return None, None

    @staticmethod
    def _get_destination_vertex_and_input_port_for_ensemble(
            nengo_connection, nengo_to_app_graph_map):
        """ Get the sink and input port for a connection terminating at a \
        ensemble.

        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :return: app vertex, and a input port enum 
        """
        operator = nengo_to_app_graph_map[nengo_connection.post_obj]
        if (isinstance(nengo_connection.pre_obj, nengo.Node) and
                not callable(nengo_connection.pre_obj.output) and
                not isinstance(nengo_connection.pre_obj.output, Process) and
                nengo_connection.pre_obj.output is not None):

            # Connections from constant valued Nodes are optimised out.
            # Build the value that will be added to the direct input for the
            # ensemble.
            val = nengo_connection.pre_obj.output[nengo_connection.pre_slice]

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
                modifies = \
                    nengo_connection.learning_rule.learning_rule_type.modifies
                if modifies == constants.ENCODERS_FLAG:
                    input_port = constants.ENSEMBLE_INPUT_PORT.LEARNT
            return operator, input_port

    @staticmethod
    def _get_destination_vertex_and_input_port_for_learning_rule(
            nengo_connection, nengo_to_app_graph_map):
        """ Get the sink and input port for a connection terminating at a \
        learning rule.
        
        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :return: app vertex, and a input port enum 
        """
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
            random_number_generator, nengo_operator_graph, live_io_senders):
        """ Get the sink and input port for a connection terminating at a Node.
        
        :param nengo_connection: the nengo connection to find the destination \
        vertex and input port  
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param host_network: the vertices and edges which will be simulated \
        on host machine.
        :param random_number_generator: the random number generator used by \
        the nengo objects
        :param nengo_operator_graph: the nengo operator graph. 
        :param live_io_senders: dict of nengo object to sdp transmitters 
        :return: app vertex, and a input port enum 
        """
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
            if nengo_connection.post_obj not in live_io_senders:

                # create new live io output operator
                operator = SDPTransmitterApplicationVertex(
                    label="sdp transmitter app vertex for nengo node {}".format(
                        nengo_connection.pre_obj.label),
                    rng=random_number_generator,
                    size_in=nengo_connection.pre_obj.size_out,
                    seed=helpful_functions.get_seed(nengo_connection.post_obj))

                # TODO solve this inheritance issue
                host_link = NengoInputNode(operator)
                with host_network:
                    if host_link not in host_network:
                        host_network.add(host_link)
                        nengo.Connection(operator, nengo_connection.post_obj,
                                         synapse=None)

                # update records
                live_io_senders[nengo_connection.pre_obj] = operator
                nengo_operator_graph.add_vertex(operator)
            else:
                operator = live_io_senders[nengo_connection.post_obj]

            # return operator and the defacto output port
            return operator, constants.INPUT_PORT.STANDARD

    def get_destination_vertex_and_input_port(
            self, nengo_connection, nengo_to_app_graph_map, host_network,
            random_number_generator, nengo_operator_graph, live_io_senders):
        """ locate the destination vertex and the port into the destination 
        vertex for this nengo connection.
        
        :param nengo_connection: the nengo connection to locate the \ 
        destination vertex and the port into the destination vertex for.
        :param nengo_to_app_graph_map: the mapping between nengo object and \
        the nengo_operator_graph (a type of application graph)
        :param host_network: the vertices and edges which will be simulated \
        on host machine.
        :param random_number_generator: the random number generator used by \
        the nengo objects
        :param nengo_operator_graph: the nengo operator graph. 
        :param live_io_senders: dict of nengo object to sdp transmitters 
        :return: app vertex, and a input port enum 
        """
        # if neurons, hand the sink of the connection
        if isinstance(nengo_connection.post_obj, nengo.ensemble.Neurons):
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
        # if a basic nengo object, hand back a basic port
        elif isinstance(nengo_connection.post_obj, NengoObject):
            return (nengo_to_app_graph_map[nengo_connection.post_obj],
                    constants.INPUT_PORT.STANDARD)
        # if a node.
        elif isinstance(nengo_connection.post_obj, nengo.Node):
            return self._get_destination_vertex_and_input_port_for_nengo_node(
                nengo_connection, nengo_to_app_graph_map,
                host_network, random_number_generator, nengo_operator_graph,
                live_io_senders=live_io_senders)

    @staticmethod
    def _make_signal_parameter(
            source_vertex, destination_vertex, nengo_connection):
        """Create connection_parameters for a signal using specifications 
        provided by the source and sink.
        
        :param source_vertex: the vertex this signals will be associated with
        :param destination_vertex: the vertex these signals will go into
        :param nengo_connection: the nengo connection which these signals are\
        associated with
        :return if latching is required, and the weight associated with the edge
        :rtype: bool, int
        """
        if (isinstance(destination_vertex, SDPReceiverApplicationVertex) or
                isinstance(source_vertex, SDPReceiverApplicationVertex)):
            return True, nengo_connection.post_obj.size_in
        else:
            return False, nengo_connection.post_obj.size_in
