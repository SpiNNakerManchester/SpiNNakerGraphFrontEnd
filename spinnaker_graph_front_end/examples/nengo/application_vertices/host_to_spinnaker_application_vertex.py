from spinnaker_graph_front_end.examples.nengo.graph_components.\
    abstract_nengo_application_vertex import AbstractNengoApplicationVertex
import nengo


class HostToSpiNNakerApplicationVertex(AbstractNengoApplicationVertex, nengo.Node):

    def __init__(self, size_in):
        AbstractNengoApplicationVertex.__init__
        self._size_in = size_in
        self._size_out = 0

    @property
    def size_in(self):
        return self._size_in

    @property
    def size_out(self):
        return self._size_out

    def output(self, _):
        """This should inform the controller of the output value of the
        target.
        """
        return value

    @property
    def target(self):
        return self._target