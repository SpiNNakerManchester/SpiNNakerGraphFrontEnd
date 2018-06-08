from pacman.model.graphs.impl import OutgoingEdgePartition
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    nengo_connection_application_edge import \
    NengoConnectionApplicationEdge


class NengoOutgoingApplicationEdgePartition(OutgoingEdgePartition):

    def __init__(
            self, identifier, transmission_parameters, key_space,
            latching=False, allowed_edge_types=None, constraints=None,
            label=None, traffic_weight=1):

        if allowed_edge_types is None:
            allowed_edge_types = [NengoConnectionApplicationEdge]
        OutgoingEdgePartition.__init__(
            self, allowed_edge_types=allowed_edge_types, identifier=identifier,
            constraints=constraints, label=label, traffic_weight=traffic_weight)
        self._transmission_parameters = transmission_parameters
        self._key_space = key_space
        self._latching = latching

    @property
    def transmission_parameters(self):
        return self._transmission_parameters

    @property
    def key_space(self):
        return self._key_space

    @property
    def latching(self):
        return self._latching
