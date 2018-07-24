from pacman.executor.injection_decorator import inject_items
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.machine_vertices. \
    sdp_receiver_machine_vertex import SDPReceiverMachineVertex
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_live_output_interface import NengoLiveOutputInterface


class SDPReceiverApplicationVertex(
        AbstractNengoApplicationVertex, NengoLiveOutputInterface):
    """An operator which receives SDP packets and transmits the contained data
    as a stream of multicast packets.
    
    ABS THIS LOOKS VERY MUCH LIKE A SPIKE INJECTOR WITH PAYLOADS!!!!!
    """

    __slots__ = [
        #
        '_connection_vertices',
        #
        "_size_in"
    ]

    def __init__(self, label, rng, size_in, seed):
        AbstractNengoApplicationVertex.__init__(
            self, label=label, rng=rng, seed=seed)
        NengoLiveOutputInterface.__init__(self)

        # Create a mapping of which connection is broadcast by which vertex
        self._connection_vertices = dict()
        self._size_in = size_in

    @property
    def size_in(self):
        return self._size_in

    @inject_items(
        {"transceiver": "MemoryTransceiver",
         "graph_mapper": "MemoryNengoGraphMapper",
         "placements": "MemoryPlacements"})
    @overrides(
        NengoLiveOutputInterface.output,
        additional_arguments={"transceiver", "graph_mapper", "placements"})
    def output(self, t, x, transceiver, graph_mapper, placements):
        for machine_vertex in graph_mapper.get_machine_vertices(self):
            placement = placements.get_placement_of_vertex(machine_vertex)
            machine_vertex.send_output_to_spinnaker(
                x, placement, transceiver)

    @inject_items({"operator_graph": "NengoOperatorGraph"})
    @overrides(
        AbstractNengoApplicationVertex.create_machine_vertices,
        additional_arguments="operator_graph")
    def create_machine_vertices(self, resource_tracker, operator_graph):
        # Get all outgoing signals and their associated transmission
        # connection_parameters

        machine_verts = list()

        outgoing_partitions = operator_graph.\
            get_outgoing_edge_partitions_starting_at_vertex(self)

        # only create vertices for output ports of standard, otherwise raise
        # exception
        for outgoing_partition in outgoing_partitions:
            if outgoing_partition.identifier.source_port == \
                    constants.OUTPUT_PORT.STANDARD:

                # Create a vertex for this connection
                machine_vertex = SDPReceiverMachineVertex(outgoing_partition)
                machine_verts.append(machine_vertex)

                # Allocate resources for this vertex
                resource_tracker.allocate_constrained_resources(
                    machine_vertex.resources_required,
                    machine_vertex.constraints)
            else:
                raise Exception(
                    "The SDP receiver does not know what to do with output"
                    " port {}".format(
                        outgoing_partition.identifier.source_port))

        return machine_verts
