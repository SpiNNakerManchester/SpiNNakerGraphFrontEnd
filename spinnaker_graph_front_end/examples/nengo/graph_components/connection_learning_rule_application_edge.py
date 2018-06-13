from pacman.model.graphs.application import ApplicationEdge
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    abstract_connection_application_edge import \
    AbstractConnectionApplicationEdge
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    abstract_nengo_object import AbstractNengoObject


class ConnectionLearningRuleApplicationEdge(
        ApplicationEdge, AbstractNengoObject,
        AbstractConnectionApplicationEdge):

    __slots__ = [
        # the learning rule associated with this application edge
        "_learning_rule"
    ]

    def __init__(self, pre_vertex, post_vertex, rng, learning_rule):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)
        AbstractNengoObject.__init__(self, rng)
        AbstractConnectionApplicationEdge.__init__(self)
        self._learning_rule = learning_rule

