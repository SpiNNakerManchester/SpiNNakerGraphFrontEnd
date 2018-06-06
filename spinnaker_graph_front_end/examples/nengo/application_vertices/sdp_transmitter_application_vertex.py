from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.machine_vertices.\
    sdp_transmitter_machine_vertex import \
    SDPTransmitterMachineVertex


class SDPTransmitterApplicationVertex(BasicNengoApplicationVertex):
    """
    LPG equiv vertex (but includes filtering and some routing stuff)
    """

    def __init__(self, size_in, label, rng):
        BasicNengoApplicationVertex.__init__(self, label=label, rng=rng)
        self._size_in = size_in
        self._vertex = None

    @overrides(BasicNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        """Create vertices that will simulate the SDPTransmitter."""
        return SDPTransmitterMachineVertex(self._size_in)
