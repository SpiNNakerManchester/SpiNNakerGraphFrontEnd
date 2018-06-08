from pacman.model.graphs.application import ApplicationEdge
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_object import BasicNengoObject


class NengoConnectionApplicationEdge(ApplicationEdge, BasicNengoObject):

    def __init__(self, pre_vertex, post_vertex, rng):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)
        BasicNengoObject.__init__(self, rng)

