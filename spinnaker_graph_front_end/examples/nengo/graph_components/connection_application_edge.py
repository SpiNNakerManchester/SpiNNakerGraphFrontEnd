from pacman.model.graphs.application import ApplicationEdge


class ConnectionApplicationEdge(ApplicationEdge):
    __slots__ = [
        #
        "_input_port",
        #
        "_reception_parameters"
    ]

    def __init__(self, pre_vertex, post_vertex, input_port,
                 reception_parameters):
        ApplicationEdge.__init__(
            self, pre_vertex=pre_vertex, post_vertex=post_vertex)
        self._input_port = input_port
        self._reception_parameters = reception_parameters

    @property
    def input_port(self):
        return self._input_port

    @property
    def reception_parameters(self):
        return self._reception_parameters
