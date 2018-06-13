from spinnaker_graph_front_end.examples.nengo.graph_components.\
    abstract_nengo_application_vertex import AbstractNengoApplicationVertex


class SpiNNakerToHostApplicationVertex(AbstractNengoApplicationVertex):

    def __init__(self, node):
        self.size_in = node.size_out
        self.size_out = 0
        self.target = node

    def output(self, value):
        """This should inform the controller of the output value of the
        target.
        """
        return value

    @property
    def target(self):
        return self._target
