from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.graph_components.basic_nengo_application_vertex import \
    BasicNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.machine_vertices.sdp_receiver_machine_vertex import \
    SDPReceiverMachineVertex


class SDPReceiver(BasicNengoApplicationVertex):
    """An operator which receives SDP packets and transmits the contained data
    as a stream of multicast packets.
    
    ABS THIS LOOKS VERY MUCH LIKE A SPIKE INJECTOR WITH PAYLOADS!!!!!
    """

    def __init__(self, label, rng):
        # Create a mapping of which connection is broadcast by which vertex
        self._connection_vertices = dict()

        BasicNengoApplicationVertex.__init__(self, label=label, rng=rng)

    @overrides(BasicNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self, nengo_app_graph):
        verts = list()

        # Get all outgoing signals and their associated transmission parameters
        for signal, transmission_params in \
                model.get_signals_from_object(self)[OutputPort.standard]:
            # Get the transform, and from this the keys
            transform = transmission_params.full_transform(slice_out=False)
            keys = [(signal, {"index": i}) for i in
                    range(transform.shape[0])]

            # Create a vertex for this connection (assuming its size out <= 64)
            if len(keys) > 64:
                raise NotImplementedError(
                    "Connection is too wide to transmit to SpiNNaker. "
                    "Consider breaking the connection up or making the "
                    "originating node a function of time Node."
                )

            verts.append(SDPReceiverMachineVertex(keys))
        return verts
