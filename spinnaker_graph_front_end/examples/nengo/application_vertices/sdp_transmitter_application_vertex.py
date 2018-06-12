import threading

import numpy

import nengo
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.graph_components. \
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.machine_vertices. \
    sdp_transmitter_machine_vertex import \
    SDPTransmitterMachineVertex
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.nengo_live_input_interface import \
    NengoLiveInputInterface


class SDPTransmitterApplicationVertex(
        BasicNengoApplicationVertex, nengo.Node, NengoLiveInputInterface):
    """
    LPG equiv vertex (but includes filtering and some routing stuff)
    """

    def __init__(self, size_in, label, rng):
        nengo.Node.__init__(self)
        BasicNengoApplicationVertex.__init__(self, label=label, rng=rng)
        self._size_in = size_in
        self._vertex = None
        self._output = numpy.zeros(self._size_out)
        self._lock = threading.Lock()

    @property
    def size_in(self):
        return self._size_in

    @overrides(NengoLiveInputInterface.output)
    def output(self, t):
        """This is a interface used by the nengo
        """
        with self._lock:
            return self._output

    def set_output(self, new_output):
        with self._lock:
            self._output = new_output

    @overrides(BasicNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        """Create vertices that will simulate the SDPTransmitter."""
        return SDPTransmitterMachineVertex(self._size_in)

    @overrides(nengo.Node.__setstate__)
    def __setstate__(self, state):
        raise NotImplementedError("Nengo objects do not support pickling")

    @overrides(nengo.Node.__getstate__)
    def __getstate__(self):
        raise NotImplementedError("Nengo objects do not support pickling")
