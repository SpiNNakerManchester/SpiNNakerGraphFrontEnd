from pacman.model.graphs.application import ApplicationVertex
from pacman.model.resources import ResourceContainer, SDRAMResource, \
    DTCMResource, CPUCyclesPerTickResource
from spinnaker_graph_front_end.examples.nengo.machine_vertices.sdp_receiver_machine_vertex import \
    SDPReceiverMachineVertex


class SDPReceiver(ApplicationVertex):
    """An operator which receives SDP packets and transmits the contained data
    as a stream of multicast packets.
    
    ABS THIS LOOKS VERY MUCH LIKE A SPIKE INJECTOR WITH PAYLOADS!!!!!
    """

    def __init__(self):
        # Create a mapping of which connection is broadcast by which vertex
        self._connection_vertices = dict()
        self._sys_regions = dict()
        self._key_regions = dict()

        ApplicationVertex.__init__(self, label="SDP_Receiver")

    def create_machine_vertices(self):


    def create_machine_vertex(
            self, vertex_slice, resources_required, label=None,
            constraints=None):
        pass

    @property
    def n_atoms(self):
        return 1

    def get_resources_used_by_atoms(self, vertex_slice):
        """ the reason why this is passed is due to a impicit requirement to 
        use the built in partitioner, which this doesnt 
        """
        pass
