import nengo
from pacman.executor.injection_decorator import inject
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.machine_vertices. \
    sdp_receiver_machine_vertex import SDPReceiverMachineVertex
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_live_output_interface import NengoLiveOutputInterface


class SDPReceiverApplicationVertex(
        AbstractNengoApplicationVertex,  nengo.Node, NengoLiveOutputInterface):
    """An operator which receives SDP packets and transmits the contained data
    as a stream of multicast packets.
    
    ABS THIS LOOKS VERY MUCH LIKE A SPIKE INJECTOR WITH PAYLOADS!!!!!
    """

    __slots__ = [
        #
        '_connection_vertices'
    ]

    def __init__(self, label, rng):
        nengo.Node.__init__(self)
        AbstractNengoApplicationVertex.__init__(self, label=label, rng=rng)
        NengoLiveOutputInterface.__init__(self)

        # Create a mapping of which connection is broadcast by which vertex
        self._connection_vertices = dict()

    @inject({"transceiver": "MemoryTransceiver",
             "graph_mapper": "MemoryNengoGraphMapper",
             "placements": "MemoryPlacements"})
    @overrides(
        NengoLiveOutputInterface.output,
        additional_arguments={"transceiver", "graph_mapper", "placements"})
    def output(self, _, value, transceiver, graph_mapper, placements):
        for machine_vertex in graph_mapper.get_machine_vertices(self):
            placement = placements.get_placement_of_vertex(machine_vertex)
            machine_vertex.send_output_to_spinnaker(
                value, placement, transceiver)

    @overrides(nengo.Node.__setstate__)
    def __setstate__(self, state):
        raise NotImplementedError("Nengo objects do not support pickling")

    @overrides(nengo.Node.__getstate__)
    def __getstate__(self):
        raise NotImplementedError("Nengo objects do not support pickling")

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
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
