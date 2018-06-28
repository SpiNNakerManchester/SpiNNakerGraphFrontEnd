import logging
from collections import defaultdict

from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import OutgoingEdgePartition
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_object import AbstractNengoObject
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_learning_rule_application_edge import \
    ConnectionLearningRuleApplicationEdge
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    destination_params import DestinationParams

logger = FormatAdapter(logging.getLogger(__name__))


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
        self._reception_params = defaultdict(list)

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
        dest_param = DestinationParams(
            destination_vertex, destination_input_port)
        if dest_param in self._reception_params:
            pass
        else:
            self._reception_params[dest_param].append(reception_params)

    def get_reception_params_for_vertex(self, destination_vertex, port_num):
        dest_param = DestinationParams(destination_vertex, port_num)
        if dest_param in self._reception_params:
            return self._reception_params[dest_param]
        else:
            return list()

    def __repr__(self):
        edges = ""
        for edge in self._edges:
            if edge.label is not None:
                edges += edge.label + ","
            else:
                edges += str(edge) + ","

        reception_params = ""
        for dest_param in self._reception_params:
            reception_params += "{}:{}".format(dest_param.dest_vertex,
                                               dest_param.dest_port)
            reception_params += "={}\n".format(
                self._reception_params[dest_param])
        return self._REPR_TEMPLATE.format(
            self._identifier, edges, self.constraints, self.label,
            reception_params, self._seed)

    def __str__(self):
        return self.__repr__()