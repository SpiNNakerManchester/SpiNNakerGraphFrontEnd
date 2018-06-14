from pacman.model.graphs.application import ApplicationEdge
from pacman.model.graphs.impl import OutgoingEdgePartition
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_connection_application_data_holder import \
    AbstractConnectionApplicationDataHolder
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_object import AbstractNengoObject
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    connection_learning_rule_application_edge import \
    ConnectionLearningRuleApplicationEdge


class ConnectionOutgoingPartition(
        OutgoingEdgePartition, AbstractConnectionApplicationDataHolder,
        AbstractNengoObject):

    __slots__ = []

    _REPR_TEMPLATE = \
        "ConnectionOutgoingPartition(\n" \
        "identifier={}, edges={}, constraints={}, label={}, " \
        "transmission_params={}, reception_params={}, latching_required={}," \
        "weight={}, source_output_port={}, destination_input_port={}, seed={})"

    def __init__(self, rng, identifier):
        OutgoingEdgePartition.__init__(
            self, identifier=identifier,
            allowed_edge_types=[
                ApplicationEdge, ConnectionLearningRuleApplicationEdge])
        AbstractConnectionApplicationDataHolder.__init__(self)
        AbstractNengoObject.__init__(self, rng=rng)

    @property
    @overrides(OutgoingEdgePartition.traffic_weight)
    def traffic_weight(self):
        return self._weight

    def __repr__(self):
        edges = ""
        for edge in self._edges:
            if edge.label is not None:
                edges += edge.label + ","
            else:
                edges += str(edge) + ","
        return self._REPR_TEMPLATE.format(
            self._identifier, edges, self.constraints, self.label,
            self._transmission_params, self._reception_params,
            self._latching_required, self._weight, self._source_output_port,
            self._destination_input_port, self._seed)

    def __str__(self):
        return self.__repr__()