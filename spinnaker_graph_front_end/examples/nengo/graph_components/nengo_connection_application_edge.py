from pacman.model.graphs.application import ApplicationEdge


class NengoConnectionApplicationEdge(ApplicationEdge):

    def __init__(self, pre_vertex, post_vertex):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)

