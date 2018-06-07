from pacman.model.graphs.machine import MachineGraph
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    pass_through_application_vertex import PassThroughApplicationVertex
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    graph_mapper import GraphMapper


class NengoPartitioner(object):
    MACHINE_GRAPH_LABEL = "machine graph"

    def __call__(self, nengo_operator_graph, skip_pass_through_nodes):
        machine_graph = MachineGraph(label=self.MACHINE_GRAPH_LABEL)
        graph_mapper = GraphMapper()

        for operator in nengo_operator_graph.vertices():

            # If the operator is a pass through Node then skip it
            if (isinstance(operator, PassThroughApplicationVertex) and
                    skip_pass_through_nodes):
                continue
            else:
                machine_vertices = operator.make_vertices()
            machine_graph.add_vertices(machine_vertices)


        # Construct nets from the signals
        nets = dict()
        id_to_signal = dict()
        for signal, transmission_parameters in \
                self.connection_map.get_signals():
            # Get the source and sink vertices
            original_sources = operator_vertices[signal.source]
            if not isinstance(original_sources, collections.Iterable):
                original_sources = (original_sources, )

            # Filter out any sources which have an `accepts_signal` method and
            # return False when this is called with the signal and transmission
            # parameters.
            sources = list()
            for source in original_sources:
                # For each source which either doesn't have a
                # `transmits_signal` method or returns True when this is called
                # with the signal and transmission parameters add a new net to
                # the netlist.
                if (hasattr(source, "transmits_signal") and not
                        source.transmits_signal(signal,
                                                transmission_parameters)):
                    pass  # This source is ignored
                else:
                    # Add the source to the final list of sources
                    sources.append(source)

            sinks = collections.deque()
            for sink in signal.sinks:
                # Get all the sink vertices
                sink_vertices = operator_vertices[sink]
                if not isinstance(sink_vertices, collections.Iterable):
                    sink_vertices = (sink_vertices, )

                # Include any sinks which either don't have an `accepts_signal`
                # method or return true when this is called with the signal and
                # transmission parameters.
                sinks.extend(s for s in sink_vertices if
                             not hasattr(s, "accepts_signal") or
                             s.accepts_signal(signal, transmission_parameters))

            # Create the net(s)
            id_to_signal[id(signal._params)] = signal  # Yuck
            nets[signal] = NMNet(sources, list(sinks), signal.weight)

        # Get the constraints on the signal identifiers
        signal_id_constraints = dict()
        for u, vs in iteritems(id_constraints):
            signal_id_constraints[id_to_signal[u]] = {
                id_to_signal[v] for v in vs
            }

        # Return a netlist
        return Netlist(
            nets=nets,
            operator_vertices=operator_vertices,
            keyspaces=self.keyspaces)