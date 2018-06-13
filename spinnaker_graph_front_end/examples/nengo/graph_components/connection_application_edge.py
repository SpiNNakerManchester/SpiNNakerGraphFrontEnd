from spinnaker_graph_front_end.examples.nengo.graph_components. \
    abstract_connection_application_edge import \
    AbstractConnectionApplicationEdge

from pacman.model.graphs.application import ApplicationEdge
from spinnaker_graph_front_end.examples.nengo.abstracts.abstract_nengo_object import \
    AbstractNengoObject


class ConnectionApplicationEdge(
        ApplicationEdge, AbstractNengoObject,
        AbstractConnectionApplicationEdge):

    __slots__ = [
    ]

    def __init__(self, pre_vertex, post_vertex, rng):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)
        AbstractNengoObject.__init__(self, rng)
        AbstractConnectionApplicationEdge.__init__(self)
