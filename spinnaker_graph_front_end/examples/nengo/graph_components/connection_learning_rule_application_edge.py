from pacman.model.graphs.application import ApplicationEdge


class ConnectionLearningRuleApplicationEdge(
        ApplicationEdge):

    __slots__ = [
        # the learning rule associated with this application edge
        "_learning_rule"
    ]

    def __init__(self, pre_vertex, post_vertex, learning_rule):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)
        self._learning_rule = learning_rule
