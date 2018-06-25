from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import OutgoingEdgePartition
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_object import AbstractNengoObject
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_learning_rule_application_edge import \
    ConnectionLearningRuleApplicationEdge


class ConnectionOutgoingPartition(OutgoingEdgePartition, AbstractNengoObject):

    __slots__ = [
        '_outgoing_edges_destinations',
        #
        '_transmission_params',
        #
        '_reception_params',
        #
        '_latching_required',
        #
        '_weight',
        #
        '_source_output_port',
    ]

    _REPR_TEMPLATE = \
        "ConnectionOutgoingPartition(\n" \
        "identifier={}, edges={}, constraints={}, label={}, " \
        "reception_params={}, seed={})"

    def __init__(self, rng, identifier, pre_vertex, seed):
        OutgoingEdgePartition.__init__(
            self, identifier=identifier,
            allowed_edge_types=(
                ApplicationEdge, ConnectionLearningRuleApplicationEdge))
        AbstractNengoObject.__init__(self, rng=rng, seed=seed)
        self._outgoing_edges_destinations = list()
        self._pre_vertex = pre_vertex
        self._reception_params = dict()

    @overrides(OutgoingEdgePartition.add_edge)
    def add_edge(self, edge):
        super(ConnectionOutgoingPartition, self).add_edge(edge)
        self._outgoing_edges_destinations.append(edge.post_vertex)

    @property
    def edge_destinations(self):
        return self._outgoing_edges_destinations

    @property
    @overrides(OutgoingEdgePartition.traffic_weight)
    def traffic_weight(self):
        return self._identifier.weight

    def add_destination_parameter_set(
            self, reception_params, destination_input_port, destination_vertex):
        self._reception_params[
            (destination_vertex, destination_input_port)] = reception_params

    def get_reception_params_for_vertex(self, destination_vertex, port_num):
        return self._reception_params[(destination_vertex, port_num)]

    def __repr__(self):
        edges = ""
        for edge in self._edges:
            if edge.label is not None:
                edges += edge.label + ","
            else:
                edges += str(edge) + ","

        reception_params = ""
        for (vertex, port) in self._reception_params:
            reception_params += "{}:{}".format(vertex, port)
            reception_params+="={}\n".format(
                self._reception_params[(vertex, port)])
        return self._REPR_TEMPLATE.format(
            self._identifier, edges, self.constraints, self.label,
            reception_params, self._seed)

    def __str__(self):
        return self.__repr__()