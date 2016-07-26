from pacman.model.partitioned_graph.partitioned_vertex import PartitionedVertex
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.sdram_resource import SDRAMResource


class ConwayBasicCell(PartitionedVertex):
    """
    cell which represents a cell within the 2 d fabric
    """

    def __init__(self, label):

        resources = ResourceContainer(sdram=SDRAMResource(0),
                                      dtcm=DTCMResource(0),
                                      cpu=CPUCyclesPerTickResource(0))
        PartitionedVertex.__init__(self, resources, label)

    def get_binary_file_name(self):
        return "conways.aplx"

