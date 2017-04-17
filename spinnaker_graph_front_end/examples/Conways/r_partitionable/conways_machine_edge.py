from pacman.model.graphs.machine.impl.machine_edge import MachineEdge


class ConwaysMachineEdge(MachineEdge):

    def __init__(
            self, synapse_information, pre_vertex, post_vertex,
            label=None, traffic_weight=1):
        MachineEdge.__init__(self, pre_vertex, post_vertex, label=label,
                             traffic_weight=traffic_weight)
        self._mapping_info = synapse_information

    def __repr__(self):
        return "{}:{}".format(self.pre_vertex, self.post_vertex)

    @property
    def mapping_info(self):
        return self._mapping_info
