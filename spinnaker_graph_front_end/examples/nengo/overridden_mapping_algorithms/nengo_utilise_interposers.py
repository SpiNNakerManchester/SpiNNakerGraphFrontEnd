from collections import deque

from pacman.model.graphs import AbstractOutgoingEdgePartition
from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import Graph
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    pass_through_application_vertex import \
    PassThroughApplicationVertex


class NengoUtiliseInterposers(object):


    def __call__(self, application_graph, nengo_to_app_graph_map):
        
        interposers, new_application_graph = self._insert_interposers(
            application_graph)
        new_application_graph = self._stack_interposers(
            new_application_graph, interposers)
        return new_application_graph, nengo_to_app_graph_map

    def _insert_interposers(self, application_graph):
        """Get a new connection map with the pass through nodes removed and with
        interposers inserted into the network at appropriate places.
        
        """
        # Create a new connection map and a store of interposers
        interposers = list()
        new_application_graph = Graph(
            allowed_vertex_types=AbstractNengoApplicationVertex,
            allowed_edge_types=ApplicationEdge,
            allowed_partition_types=AbstractOutgoingEdgePartition,
            label=constants.INTER_APP_GRAPH_NAME)

        # For every clique in this connection map we identify which connections
        # to replace with interposers and then insert the modified connectivity
        # into the new connection map.
        for sources, nodes in self._get_cliques(application_graph):
            # Extract all possible interposers from the clique. Interposers can
            # either replace connections from passthrough nodes or the
            # "transform" portion of the connection from an ensemble.

            possible_interposers = (
                (node, port, conn, {s.sink_object for s in sinks})
                for node in chain(
                nodes, (e for e in sources if isinstance(e, EnsembleLIF))
            )
                for port, conns in iteritems(
                self._connections[node])
                for conn, sinks in iteritems(conns)
            )

            # Of these possible connections determine which would benefit from
            # replacement with interposers. For these interposers build a set
            # of other potential interposers whose input depends on the output
            # of the interposer.
            potential_interposers = dict()
            for node, port, conn, sink_objects in possible_interposers:
                _, tps = conn  # Extract the transmission parameters

                # Determine if the interposer connects to anything
                if not self._connects_to_non_passthrough_node(sink_objects):
                    continue

                # For each connection look at the fan-out and fan-in vs the
                # cost of the interposer.
                trans = tps.full_transform(False, False)
                mean_fan_in = np.mean(np.sum(trans != 0.0, axis=0))
                mean_fan_out = np.mean(np.sum(trans != 0.0, axis=1))
                interposer_fan_in = np.ceil(
                    float(trans.shape[1]) / float(128))
                interposer_fan_out = np.ceil(
                    float(trans.shape[0]) / float(64))

                # If the interposer would improve connectivity then add it to
                # the list of potential interposers.
                if (mean_fan_in > interposer_fan_in or
                            mean_fan_out > interposer_fan_out):
                    # Store the potential interposer along with a list of nodes
                    # who receive its output.
                    potential_interposers[(node, port, conn)] = [
                        s for s in sink_objects
                        if isinstance(s, PassthroughNode)
                    ]

            # Get the set of potential interposers whose input is independent
            # of the output of any other interposer.
            top_level_interposers = set(potential_interposers)
            for dependent_interposers in itervalues(potential_interposers):
                # Subtract from the set of independent interposers any whose
                # input node is listed in the output nodes for another
                # interposer.
                remove_interposers = {
                    (node, port, conn) for (node, port, conn) in
                    top_level_interposers if node in dependent_interposers
                }
                top_level_interposers.difference_update(remove_interposers)

            # Create an operator for all of the selected interposers
            clique_interposers = dict()
            for node, port, conn in top_level_interposers:
                # Extract the input size
                _, transmission_pars = conn
                size_in = transmission_pars.size_in

                # Create the interposer
                clique_interposers[node, port, conn] = Filter(size_in)

            # Insert connections into the new connection map inserting
            # connections to interposers as we go and remembering those to
            # which a connection is added.
            used_interposers = set()  # Interposers who receive non-zero input
            for source in sources:
                used_interposers.update(
                    self._copy_connections_from_source(
                        source=source, target_map=new_application_graph,
                        interposers=clique_interposers
                    )
                )

            # Insert connections from the new interposers.
            for (node, port, conn) in used_interposers:
                # Get the interposer, add it to the new operators to include in
                # the model and add its output to the new connection map.
                interposer = clique_interposers[(node, port, conn)]
                interposers.append(interposer)

                # Add outgoing connections
                self._copy_connections_from_interposer(
                    node=node, port=port, conn=conn, interposer=interposer,
                    target_map=new_application_graph
                )

        return interposers, new_application_graph

    @staticmethod
    def _get_cliques(application_graph):
        """Extract cliques of connected nodes from the original graph.

        For example, the following network consists of two cliques:

            1 ->-\    /->- 5 ->-\
            2 ->--> 4 -->- 6 ->--> 8 ->- 9
            3 ->-/    \->- 7 ->-/

            \=======v=====/\=======v======/
                Clique 1       Clique 2

        Where 4, 8 and 9 are passthrough nodes.

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
        for vertex in application_graph.vertices:
            if (application_graph.n_outgoing_edge_partitions() != 0 and
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
            # provides input and if it's a passthrough node then we care about
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
                    for application_edge in application_graph.\
                            get_edges_ending_at_vertex(node):
                        if (application_edge.pre_vertex not in sources and
                                application_edge.pre_vertex not in
                                pass_through_nodes):
                            queue.extend((True, application_edge.pre_vertex))
                if queue_sinks:
                    for application_edge in application_graph.\
                            get_edges_starting_at_vertex(node):
                        if (application_edge.post_vertex not in sinks and
                                application_edge.post_vertex not in
                                pass_through_nodes):
                            queue.extend((False, application_edge.pre_vertex))

            # Once the queue is empty we yield the contents of the clique
            unvisited_sources.difference_update(sources)
            yield sources, pass_through_nodes
