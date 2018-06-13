from pacman.model.graphs.application import ApplicationEdge
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_object import BasicNengoObject


class ConnectionLearningRuleApplicationEdge(ApplicationEdge, BasicNengoObject):

    __slots__ = [
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
        #
        '_destination_input_port',
        #
        "_learning_rule"
    ]

    def __init__(self, pre_vertex, post_vertex, rng, learning_rule):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)
        BasicNengoObject.__init__(self, rng)
        self._transmission_params = None
        self._reception_params = None
        self._latching_required = None
        self._weight = None
        self._source_output_port = None
        self._destination_input_port = None
        self._learning_rule = learning_rule

    def set_parameters(
            self, transmission_params, reception_params, latching_required,
            weight, source_output_port, destination_input_port):
        self._transmission_params = transmission_params
        self._reception_params = reception_params
        self._latching_required = latching_required
        self._weight = weight
        self._source_output_port = source_output_port
        self._destination_input_port = destination_input_port
