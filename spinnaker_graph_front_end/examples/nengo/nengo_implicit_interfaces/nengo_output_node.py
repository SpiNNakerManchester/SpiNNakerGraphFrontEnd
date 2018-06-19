import nengo
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_live_output_interface import \
    NengoLiveOutputInterface


class NengoOutputNode(nengo.Node, NengoLiveOutputInterface):

    def __init__(self, spinnaker_vertex, size_in):
        NengoLiveOutputInterface.__init__(self)
        self._spinnaker_vertex = spinnaker_vertex
        self._size_in = size_in

    @property
    def size_in(self):
        return self._size_in

    @overrides(NengoLiveOutputInterface.output)
    def output(self, t, x):
        """ enforced by the nengo duck typing

        :param t: 
        :param x:
        :return: 
        """
        return self._spinnaker_vertex.output(t, x)
