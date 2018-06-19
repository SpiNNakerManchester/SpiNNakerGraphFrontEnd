import nengo
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.\
    nengo_implicit_interfaces.nengo_live_input_interface import \
    NengoLiveInputInterface


class NengoInputNode(nengo.Node, NengoLiveInputInterface):

    def __init__(self, spinnaker_vertex):
        nengo.Node.__init__(self)
        NengoLiveInputInterface.__init__(self)
        self._spinnaker_vertex = spinnaker_vertex

    @property
    def size_in(self):
        return self._spinnaker_vertex.size_in

    @overrides(NengoLiveInputInterface.output)
    def output(self, t):
        """ enforced by the nengo duck typing

        :param t: 
        :return: 
        """
        self._spinnaker_vertex.output(t)

    @overrides(nengo.Node.__getstate__)
    def __getstate__(self):
        pass

    @overrides(nengo.Node.__setstate__)
    def __setstate__(self, state):
        pass
