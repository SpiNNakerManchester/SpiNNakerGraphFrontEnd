from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, CPUCyclesPerTickResource
from pacman.model.resources import DTCMResource, SDRAMResource


class ConwayBasicCell(MachineVertex):
    """ Cell which represents a cell within the 2d fabric
    """

    def __init__(self, label):
        resources = ResourceContainer(sdram=SDRAMResource(0),
                                      dtcm=DTCMResource(0),
                                      cpu_cycles=CPUCyclesPerTickResource(0))
        MachineVertex.__init__(self, resources, label)
