from collections import deque, defaultdict
import itertools
from six import itervalues, iteritems
import numpy

from pacman.model.graphs import AbstractOutgoingEdgePartition
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import Graph
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    interposer_application_vertex import \
    InterposerApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    lif_application_vertex import LIFApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    pass_through_application_vertex import PassThroughApplicationVertex
from spinnaker_graph_front_end.examples.nengo.connection_parameters.\
    pass_through_node_transmission_parameters import \
    PassthroughNodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters.\
    reception_parameters import ReceptionParameters
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_outgoing_partition import ConnectionOutgoingPartition
from spinnaker_graph_front_end.examples.nengo.connection_parameters.\
    ensemble_transmission_parameters import EnsembleTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.utility_objects.\
    parameter_transform import ParameterTransform


class NengoUtiliseInterposers(object):
    """ interposers are used to reduce the connectivity, allowing 
    applications such as spawn to operate with less connectivity.
    
    """

    NEW_PARTITION_TRANSFORM_VALUE = 1.0
    INTERPOSER_LEARNING_RULE = None
    INTERPOSER_PARAMETER_FILTER = None

    def __call__(
            self, application_graph, nengo_to_app_graph_map,
            random_number_generator):

        # add interposers as required
        interposers, interposer_application_graph = \
            self._insert_interposers(
                application_graph, random_number_generator)

        # compress interposers when applicable
        stacked_interposer_graph = self._stack_interposers(
            interposer_application_graph, interposers, random_number_generator)

        # return optimised app graph
        return stacked_interposer_graph

    def _insert_interposers(self, application_graph, random_numer_generator):
        """Get a new connection map with the pass through nodes removed and with
        interposers inserted into the network at appropriate places.
        
        """
        # Create a new connection map and a store of interposers
        interposers = list()
        interposer_application_graph = Graph(
            allowed_vertex_types=AbstractNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=constants.INTER_APP_GRAPH_NAME)

        # add all but pass through nodes into the new app graph
        for vertex in application_graph.vertices:
            if not isinstance(vertex, PassThroughApplicationVertex):
                interposer_application_graph.add_vertex(vertex)

        # For every clique in this connection map we identify which connections
        # to replace with interposers and then insert the modified connectivity
        # into the new connection map.
        for sources, pass_through_app_verts in self._get_cliques(
                application_graph):
            # Extract all possible interposers from the clique. Interposers can
            # either replace connections from pass through nodes or the
            # "transform" portion of the connection from an ensemble.

            possible_interposers = list()
            for operator in itertools.chain(
                    pass_through_app_verts, (e for e in sources if isinstance(
                        e, LIFApplicationVertex))):
                for outgoing_partition in application_graph.\
                        get_outgoing_edge_partitions_starting_at_vertex(
                            operator):
                    sinks = set(outgoing_partition.edge_destinations)
                    possible_interposers.append(
                        (operator, outgoing_partition, sinks))

            # Of these possible connections determine which would benefit from
            # replacement with interposers. For these interposers build a set
            # of other potential interposers whose input depends on the output
            # of the interposer.
            potential_interposers = dict()
            for node, outgoing_partition, sink_objects in possible_interposers:
                for transmission_parameters in \
                        outgoing_partition.transmission_params:

                    # Determine if the interposer connects to anything
                    if not self._connects_to_non_pass_through_node(
                            sink_objects, application_graph):
                        continue

                    # For each connection look at the fan-out and fan-in vs the
                    # cost of the interposer.
                    trans = transmission_parameters.full_transform(False, False)
                    mean_fan_in = numpy.mean(numpy.sum(trans != 0.0, axis=0))
                    mean_fan_out = numpy.mean(numpy.sum(trans != 0.0, axis=1))
                    interposer_fan_in = numpy.ceil(
                        float(trans.shape[1]) / float(constants.MAX_COLUMNS))
                    interposer_fan_out = numpy.ceil(
                        float(trans.shape[0]) / float(constants.MAX_ROWS))

                    # If the interposer would improve connectivity then add it
                    #  to the list of potential interposers.
                    if (mean_fan_in > interposer_fan_in or
                            mean_fan_out > interposer_fan_out):
                        # Store the potential interposer along with a list of
                        #  nodes who receive its output.
                        potential_interposers[(node, outgoing_partition)] = [
                            s for s in sink_objects if isinstance(
                                s, PassThroughApplicationVertex)]

            # Get the set of potential interposers whose input is independent
            # of the output of any other interposer.
            top_level_interposers = set(potential_interposers)
            for dependent_interposers in itervalues(potential_interposers):
                # Subtract from the set of independent interposers any whose
                # input node is listed in the output nodes for another
                # interposer.
                remove_interposers = {
                    (node, outgoing_partition) for (node, outgoing_partition) in
                    top_level_interposers if node in dependent_interposers
                }
                top_level_interposers.difference_update(remove_interposers)

            # Create an operator for all of the selected interposers
            clique_interposers = dict()
            for node, outgoing_partition in top_level_interposers:
                # Extract the input size
                for transmission_par in \
                        outgoing_partition.transmission_parameters:
                    size_in = transmission_par.size_in

                    # Create the interposer
                    clique_interposers[node, outgoing_partition] = \
                        InterposerApplicationVertex(
                            size_in, rng=random_numer_generator,
                            label="Interposer for node {} in channel {}".format(
                                node, outgoing_partition))

            # Insert connections into the new connection map inserting
            # connections to interposers as we go and remembering those to
            # which a connection is added.
            used_interposers = set()  # Interposers who receive non-zero input
            for source in sources:
                used_interposers.update(
                    self._copy_connections_from_source(
                        source=source,
                        interposer_application_graph=(
                            interposer_application_graph),
                        interposers=clique_interposers,
                        original_operator_graph=application_graph,
                        random_number_generator=random_numer_generator))

            # Insert connections from the new interposers.
            for (node, outgoing_partition) in used_interposers:
                # Get the interposer, add it to the new operators to include in
                # the model and add its output to the new connection map.
                interposer = clique_interposers[(node, outgoing_partition)]
                interposers.append(interposer)

                # Add outgoing connections
                self._copy_connections_from_interposer(
                    node=node, outgoing_partition=outgoing_partition,
                    interposer=interposer,
                    new_app_graph=interposer_application_graph,
                    random_number_generator=random_numer_generator,
                    old_app_graph=application_graph)

        return interposers, interposer_application_graph

    def _create_new_connection_and_outgoing_partition(
            self, transmission_param, new_outgoing_edge_partition, interposer,
            outgoing_edge_partition, interposer_application_graph, source,
            used_interposers):
        # create new transmission_params
        new_transmission_param = EnsembleTransmissionParameters(
            transmission_param.decoders,
            ParameterTransform(
                transmission_param.size_in, transmission_param.size_in,
                self.NEW_PARTITION_TRANSFORM_VALUE))
        new_transmission_param, destination_input_port = \
            new_transmission_param.update_to_global_inhibition_if_required(
                constants.INPUT_PORT.STARNDARD)

        # update the outgoing parttion params
        new_outgoing_edge_partition.add_parameter_set(
            transmission_params=new_transmission_param,
            reception_params=ReceptionParameters(
                self.INTERPOSER_PARAMETER_FILTER,
                transmission_param.size_in,
                self.INTERPOSER_LEARNING_RULE),
            latching_required=False,
            weight=new_transmission_param.size_in,
            source_output_port=outgoing_edge_partition.identifier,
            destination_input_port=destination_input_port,
            destination_vertex=interposer)

        # add interposer and edge to it in to the new app graph
        interposer_application_graph.add_vertex(interposer)
        interposer_application_graph.add_edge(
            ApplicationEdge(source, interposer),
            new_outgoing_edge_partition.identifier)

        # update the used interposers
        used_interposers.add((source, new_outgoing_edge_partition))

    def _copy_connections_from_source(
            self, source, interposer_application_graph, interposers,
            original_operator_graph, random_number_generator):
        """
        """
        used_interposers = set()  # Interposers fed by this object

        # For every port and set of connections originating at the source
        for outgoing_edge_partition in original_operator_graph.\
                get_outgoing_edge_partitions_starting_at_vertex(source):
            if (source, outgoing_edge_partition) in interposers:
                # If this connection is to be replaced by an interposer
                # then we instead add a connection to the interposer, the
                # nature of this connection depends on the nature of the
                # source.
                assert isinstance(source, LIFApplicationVertex)
                interposer = interposers[(source, outgoing_edge_partition)]

                # create new partition for channel data holder
                new_outgoing_edge_partition = ConnectionOutgoingPartition(
                    rng=random_number_generator, pre_vertex=source,
                    identifier=outgoing_edge_partition.identifier)
                interposer_application_graph.add_outgoing_edge_partition(
                    new_outgoing_edge_partition)

                for transmission_param in \
                        outgoing_edge_partition.transmission_params:
                    self._create_new_connection_and_outgoing_partition(
                        transmission_param, new_outgoing_edge_partition,
                        interposer, outgoing_edge_partition,
                        interposer_application_graph, source, used_interposers)
            else:
                # Otherwise we add the connection.
                # Copy the connections and mark which interposers are
                # reached.
                for sink in outgoing_edge_partition.edge_destinations:
                    # NOTE: The None indicates that no additional reception
                    # connection_parameters beyond those in the sink are to be
                    # considered.
                    used_interposers.update(self._copy_connection(
                        interposer_application_graph=(
                            interposer_application_graph),
                        interposers=interposers, source_vertex=source,
                        source_port=outgoing_edge_partition.identifier,
                        destination_transmission_pars=(
                            outgoing_edge_partition.transmission_params),
                        destination_vertex=sink,
                        random_number_generator=random_number_generator,
                        original_operator_graph=original_operator_graph,
                        required_latching=(
                            outgoing_edge_partition.latching_required),
                        weight=outgoing_edge_partition.weight,
                        destination_reception_params=(
                            outgoing_edge_partition.reception_params),
                        destination_port=(
                            outgoing_edge_partition.destination_input_port)))
        return used_interposers

    def _copy_connections_from_interposer(
            self, node, outgoing_partition, interposer, new_app_graph,
            random_number_generator, old_app_graph):

        """Copy the pattern of connectivity from a node, replacing a specific
        connection with an interposer.
        """
        # Get the sinks of this connection
        sinks = list()
        for application_edge in outgoing_partition.edges:
            sinks.append(application_edge.post_vertex)

        # If the original object was an ensemble then modify the transmission
        # connection_parameters to remove the decoders.
        transmission_pars = outgoing_partition.transmission_params
        if isinstance(node, LIFApplicationVertex):
            transmission_pars = PassthroughNodeTransmissionParameters(
                outgoing_partition.transmission_params.transform)

        # Copy the connections to the sinks, note that we specify an empty
        # interposers dictionary so that no connections to further interposers
        # are inserted, likewise we specify no additional reception
        # connection_parameters. The connectivity from the sink will be
        # recursively found if it is a pass through node.
        for sink in sinks:
            self._copy_connection(
                interposer_application_graph=new_app_graph,
                interposers=interposer, source_vertex=node,
                source_port=constants.OUTPUT_PORT.STANDARD,
                required_latching=outgoing_partition.latching_required,
                weight=outgoing_partition.weight,
                destination_transmission_pars=transmission_pars,
                destination_vertex=sink.sink_object,
                destination_port=outgoing_partition.destination_input_port,
                destination_reception_params=(
                    outgoing_partition.reception_params),
                random_number_generator=random_number_generator,
                original_operator_graph=old_app_graph)

    def _copy_connection(
            self, interposer_application_graph, interposers,
            source_vertex, source_port, required_latching, weight,
            destination_transmission_pars, destination_vertex, destination_port,
            destination_reception_params, random_number_generator,
            original_operator_graph):

        """Copy a single connection from this connection map to another,
           acting recursively if an appropriate node is identified.
        """
        used_interposers = set()  # Reached interposers

        if not isinstance(destination_vertex, PassThroughApplicationVertex):
            # If the sink is not a pass through node then just add the
            # connection to the new connection map.
            # create new partition for channel data holder
            new_outgoing_edge_partition = interposer_application_graph.\
                get_outgoing_edge_partition_starting_at_vertex(
                    source_vertex, source_port)
            if new_outgoing_edge_partition is None:
                new_outgoing_edge_partition = ConnectionOutgoingPartition(
                    rng=random_number_generator, identifier=source_port,
                    pre_vertex=source_vertex)
                interposer_application_graph.add_outgoing_edge_partition(
                    new_outgoing_edge_partition)
            interposer_application_graph.add_edge(
                ApplicationEdge(source_vertex, destination_vertex), source_port)
            new_outgoing_edge_partition.add_parameter_set(
                transmission_params=destination_transmission_pars,
                reception_params=destination_reception_params,
                latching_required=required_latching, weight=weight,
                destination_input_port=destination_port,
                destination_vertex=destination_vertex)
        else:
            # If the sink is a pass through node then we consider each outgoing
            # connection in turn. If the connection is to be replaced by an
            # interposer then we add a connection to the relevant interposer,
            # otherwise we recurse to add further new connections.
            for outgoing_partition in original_operator_graph.\
                    get_outgoing_edge_partitions_starting_at_vertex(
                        destination_vertex):

                destination_vertex_destinations = list()
                for application_edge in outgoing_partition.edges:
                    destination_vertex_destinations.append(
                        application_edge.post_vertex)

                interposer = interposers.get(destination_vertex)
                if interposer is not None:
                    # If the sink is not a pass through node then just add the
                    # connection to the new connection map.
                    # create new partition for channel data holder
                    new_outgoing_edge_partition = ConnectionOutgoingPartition(
                        rng=random_number_generator, pre_vertex=source_vertex,
                        identifier=outgoing_partition.identifier)
                    interposer_application_graph.add_outgoing_edge_partition(
                        new_outgoing_edge_partition)
                    interposer_application_graph.add_vertex(interposer)
                    interposer_application_graph.add_edge(
                        ApplicationEdge(source_vertex, interposer),
                        outgoing_partition.identifier)

                    # update all parameters
                    for (transmission_params, reception_params,
                            latching_required, weight) in zip(
                                outgoing_partition.transmission_params,
                                outgoing_partition.reception_params,
                                outgoing_partition.latching_required,
                                outgoing_partition.weight):

                        new_outgoing_edge_partition.add_parameter_set(
                            transmission_params=transmission_params,
                            reception_params=reception_params,
                            latching_required=latching_required,
                            weight=weight,
                            destination_input_port=(
                                constants.INPUT_PORT.STARNDARD),
                            destination_vertex=interposer)

                    # Mark the interposer as reached
                    used_interposers.add(
                        (destination_vertex, new_outgoing_edge_partition))
                else:

                    self._merge_connection_and_try_again(
                        outgoing_partition, destination_vertex_destinations,
                        used_interposers, interposer_application_graph,
                        interposers, source_vertex, source_port,
                        required_latching, random_number_generator,
                        original_operator_graph)

        return used_interposers

    def _merge_connection_and_try_again(
            self, outgoing_partition, destination_vertex_destinations,
            used_interposers, interposer_application_graph, interposers,
            source_vertex, source_port, required_latching,
            random_number_generator, original_operator_graph):
        # Build the new signal and transmission parameters.
        destination_transmission_pars = outgoing_partition.transmission_params.\
            concat(outgoing_partition.transmission_params)

        if destination_transmission_pars is not None:

            # Add onward connections if the transmission
            # parameters aren't empty.
            for new_sink in destination_vertex_destinations:
                # Build the reception parameters and recurse
                sink_reception_params = outgoing_partition. \
                    reception_params.concat(outgoing_partition.reception_params)

                # recursive call
                used_interposers.update(self._copy_connection(
                    interposer_application_graph=interposer_application_graph,
                    interposers=interposers, source_vertex=source_vertex,
                    source_port=source_port, weight=outgoing_partition.weight,
                    required_latching=(
                        outgoing_partition.latching or required_latching),
                    destination_transmission_pars=destination_transmission_pars,
                    destination_vertex=new_sink.sink_object,
                    destination_port=new_sink.port,
                    destination_reception_params=sink_reception_params,
                    random_number_generator=random_number_generator,
                    original_operator_graph=original_operator_graph))

    def _connects_to_non_pass_through_node(
            self, sink_objects, application_graph):
        """Determine whether any of the sink objects are not pass through nodes,
        or if none are whether those pass through nodes eventually connect to a
        non-pass through node.
        """
        # Extract pass through nodes from the sinks
        pass_through_application_verts = [
            sink for sink in sink_objects if isinstance(
                sink, PassThroughApplicationVertex)]

        # If any of the sink objects are not pass through nodes then return
        if len(pass_through_application_verts) < len(sink_objects):
            return True
        else:
            # Otherwise loop over the connections from each connected
            # pass through node and see if any of those connect to a sink.
            for pass_through_node in pass_through_application_verts:
                outgoing_partitions = application_graph.\
                    get_outgoing_edge_partitions_starting_at_vertex(
                        pass_through_node)
                for outgoing_partition in outgoing_partitions:
                    sink_operators = list()
                    for application_edge in outgoing_partition.edges:
                        if application_edge.post_vertex in sink_objects:
                            sink_operators.append(application_edge.post_vertex)
                        if self._connects_to_non_pass_through_node(
                                sink_operators, application_graph):
                            return True
        # Otherwise return false to indicate that a non-pass through node object
        # is never reached.
        return False

    @staticmethod
    def _get_cliques(original_application_graph):
        """Extract cliques of connected nodes from the original graph.

        For example, the following network consists of two cliques:

            1 ->-\    /->- 5 ->-\
            2 ->--> 4 -->- 6 ->--> 8 ->- 9
            3 ->-/    \->- 7 ->-/

            \=======v=====/\=======v======/
                Clique 1       Clique 2

        Where 4, 8 and 9 are pass through nodes.

        Clique 1 has the following sources: {1, 2, 3}
        Clique 2 has the sources: {5, 6, 7}

        Adding a recurrent connection results in there being a single clique:

                    /-<------------------<--\
                    |                       |
            1 ->-\  v /->- 5 ->-\           |
            2 ->--> 4 -->- 6 ->--> 8 ->- 9 -/
            3 ->-/    \->- 7 ->-/

        Where the sources are: {1, 2, 3, 5, 6, 7}

        Yields
        ------
        ({source, ...}, {Node, ...})
            A set of objects which form the inputs to the clique and the set of
            pass through nodes contained within the clique (possibly empty).
        """

        # Construct a set of source objects which haven't been visited
        unvisited_sources = set()
        for vertex in original_application_graph.vertices:
            if (original_application_graph.n_outgoing_edge_partitions != 0 and
                    not isinstance(vertex, PassThroughApplicationVertex)):
                unvisited_sources.add(vertex)

        # While unvisited sources remain inspect the graph.
        while unvisited_sources:

            # Set of objects which feed the clique
            sources = set()

            # Pass through nodes contained in the clique
            pass_through_nodes = set()

            # Set of objects which receive values
            sinks = set()

            # Each node that is visited in the following breadth-first search
            # is treated as EITHER a source or a sink node. If the node is a
            # sink then we're interested in connected nodes which provide its
            # input, if it's a source then we care about nodes to which it
            # provides input and if it's a pass through node then we care about
            # both.
            queue = deque()  # Queue of nodes to visit
            queue.append((True, unvisited_sources.pop()))  # Add a source

            while len(queue) > 0:  # While there remain items in the queue
                is_source, node = queue.pop()  # Get an item from the queue
                queue_sources = queue_sinks = False

                if (isinstance(node, PassThroughApplicationVertex) and
                        node not in pass_through_nodes):
                    # If the node is a pass through node then we add it to the
                    # set of pass through nodes and then add both objects which
                    # feed it and those which receive from it to the queue.
                    pass_through_nodes.add(node)
                    queue_sources = queue_sinks = True
                elif (not isinstance(node, PassThroughApplicationVertex) and
                        is_source and node not in sources):
                    # If the node is a source then we add it to the set of
                    # sources for the clique and then add all objects which it
                    # feeds to the queue.
                    sources.add(node)
                    queue_sinks = True
                elif (not isinstance(node, PassThroughApplicationVertex) and
                        not is_source and node not in sinks):
                    # If the node is a sink then we add it to the set of sinks
                    # for the clique and add all objects which feed it to the
                    # queue.
                    sinks.add(node)
                    queue_sources = True

                # Queue the selected items
                if queue_sources:
                    for application_edge in original_application_graph.\
                            get_edges_ending_at_vertex(node):
                        if (application_edge.pre_vertex not in sources and
                                application_edge.pre_vertex not in
                                pass_through_nodes):
                            queue.append((True, application_edge.pre_vertex))
                if queue_sinks:
                    for application_edge in original_application_graph.\
                            get_edges_starting_at_vertex(node):
                        if (application_edge.post_vertex not in sinks and
                                application_edge.post_vertex not in
                                pass_through_nodes):
                            queue.append((False, application_edge.pre_vertex))

            # Once the queue is empty we yield the contents of the clique
            unvisited_sources.difference_update(sources)
            yield sources, pass_through_nodes

    def _stack_interposers(
            self, interposer_application_graph, interposers,
            random_number_generator):
        """Return a new list of interposers and a new communication map
        resulting from combining compatible interposers.

        Returns
        -------
        ([Interposer, ...], ConnectionMap)
            A collection of new interposer operators and a new connection map
            with compatible interposers stacked.
        """
        # Determine which interposers can be stacked and build a map of
        # {interposer: (StackedInterposer, offset)}. Using this information we
        # copy signals from the old connection map into the new connection map,
        # replacing connections to stacked interposers by modifying their
        # output slice and stacking the connections from interposers in a
        # similar manner.

        # Create a mapping {{(sig params, sink), ...}: [Interposer, ...], ...}
        # to determine which interposers can be stacked (as they have a common
        # output set).
        compatible_interposers = defaultdict(list)
        for interposer in interposers:
            # Build up a set of the outputs for each interposer.
            outgoing_partition = interposer_application_graph.\
                get_outgoing_edge_partition_starting_at_vertex(
                    interposer, constants.OUTPUT_PORT.STANDARD)
            compatible_interposers[outgoing_partition].append(interposer)

        # For each group of compatible interposers create a new, stacked,
        # interposer.
        stacked_interposers = dict()  # {StackedInterposer: [Interposer,...]}
        stacking = dict()  # {Interposers: (StackedInterposer, offset)}
        for interposer_group in itervalues(compatible_interposers):
            # Create the new interposer
            new_interposer = InterposerApplicationVertex(
                sum(i.size_in for i in interposer_group),
                label="stacked interposer for the interposer group{}".format(
                    interposer_group), rng=random_number_generator)

            stacked_interposers[new_interposer] = interposer_group

            # Store a mapping from the original interposers to the new
            # interposer and their offset into its input space.
            offset = 0
            for interposer in interposer_group:
                stacking[interposer] = (new_interposer, offset)
                offset += interposer.size_in  # Increase the offset

        # Create a new app graph and copy connections into it.
        stacked_interposer_graph = Graph(
            allowed_vertex_types=AbstractNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=constants.INTER_APP_GRAPH_NAME)

        # add none interposer vertices
        for vertex in interposer_application_graph.vertices:
            if isinstance(vertex, InterposerApplicationVertex):
                continue

            for outgoing_partition in \
                    interposer_application_graph.outgoing_edge_partitions:
                source_vertex = outgoing_partition.pre_vertex

                # only process none interposers sources
                if source_vertex not in stacking:
                    self._process_stackable_interposer(
                        outgoing_partition, stacking, random_number_generator,
                        stacked_interposer_graph, source_vertex)

        # For each stacked interposer build up a mapping from sinks, reception
        # parameters and signal parameters to the transmission parameters that
        # target it for each unstacked interposer. Subsequently stack these
        # transmission parameters and add the resulting signal to the network.
        for new_interposer, interposer_group in iteritems(stacked_interposers):
            # Map from (sink, signal_parameters) to an ordered list of
            # transmission parameters.
            connections = defaultdict(list)

            for old_interposer in interposer_group:
                outgoing_partitions = interposer_application_graph.\
                    get_outgoing_edge_partitions_starting_at_vertex(
                        old_interposer)

                for outgoing_partition in outgoing_partitions:
                    out_going_partition_destinations = \
                        outgoing_partition.edge_destinations
                    for destination_vertex in out_going_partition_destinations:
                        connections[
                            (destination_vertex,
                             outgoing_partition.latching_required,
                             outgoing_partition.weight)].append(
                            outgoing_partition.transmission_params)

            # For each unique pair of sink and signal parameters add a new
            # connection to the network which is the result of stacking
            # together the transmission parameters.
            for (destination_vertex, latching_required, weight), trans_pars in \
                    iteritems(connections):

                # Construct the combined signal parameters
                transmission_params = trans_pars[0].hstack(*trans_pars[1:])

                # set up new outgoing partition with correct params
                stacked_outgoing_partition = \
                    ConnectionOutgoingPartition(
                        identifier=outgoing_partition.identifer,
                        rng=random_number_generator)
                stacked_outgoing_partition.set_all_parameters(
                    transmission_params=transmission_params,
                    reception_params=outgoing_partition.reception_params,
                    latching_required=latching_required, weight=weight,
                    source_output_port=outgoing_partition.source_output_port,
                    destination_input_port=(
                        outgoing_partition.destination_input_port))

                # add to the graph
                stacked_interposer_graph.add_outgoing_edge_partition(
                    stacked_outgoing_partition)
                stacked_interposer_graph.add_edge(
                    ApplicationEdge(new_interposer, destination_vertex),
                    outgoing_partition.identifer)

        return stacked_interposer_graph

    def _process_stackable_interposer(
            self, outgoing_partition, stacking, random_number_generator,
            stacked_interposer_graph, source_vertex):
        # get true mc edge destinations
        connection_destinations = outgoing_partition.edge_destinations

        # Add connections to the new connection map, if they target
        # an interposer then modify the connection by projecting
        # it into the space of the new interposer.
        for connection_destination in connection_destinations:
            if connection_destination in stacking:
                # If the destination is an interposer then add a
                # modified connection to the new interposer.
                connection_interposer, offset = \
                    stacking[connection_destination]

                # Create a interposer_transmission_parameters to apply.
                slice_out = slice(
                    offset,
                    outgoing_partition.transmission_params.size_out +
                    offset)
                interposer_transmission_parameters = \
                    PassthroughNodeTransmissionParameters(
                        ParameterTransform(
                            size_in=(
                                outgoing_partition.transmission_params.
                                size_out),
                            size_out=connection_interposer.size_in,
                            transform=(
                                self.NEW_PARTITION_TRANSFORM_VALUE),
                            slice_out=slice_out))

                # Get the new transmission parameters
                interposer_transmission_parameters = \
                    outgoing_partition.transmission_params.concat(
                        interposer_transmission_parameters)
                assert interposer_transmission_parameters is not None

                # set up new outgoing partition with correct params
                stacked_outgoing_partition = \
                    ConnectionOutgoingPartition(
                        identifier=outgoing_partition.identifer,
                        rng=random_number_generator)
                stacked_outgoing_partition.set_all_parameters(
                    transmission_params=interposer_transmission_parameters,
                    reception_params=outgoing_partition.reception_params,
                    latching_required=outgoing_partition.latching_required,
                    weight=outgoing_partition.weight,
                    source_output_port=outgoing_partition.source_output_port,
                    destination_input_port=(
                        outgoing_partition.destination_input_port))

                # add to the graph
                stacked_interposer_graph.add_outgoing_edge_partition(
                    stacked_outgoing_partition)
                stacked_interposer_graph.add_edge(
                    ApplicationEdge(source_vertex, connection_interposer),
                    outgoing_partition.identifer)

            else:  # Otherwise just add the signal unchanged
                stacked_interposer_graph.add_outgoing_edge_partition(
                    outgoing_partition)
                stacked_interposer_graph.add_edge(
                    ApplicationEdge(source_vertex, connection_destination),
                    outgoing_partition.identifer)
