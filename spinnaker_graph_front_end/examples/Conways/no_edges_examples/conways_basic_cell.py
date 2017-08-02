from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer


class ConwayBasicCell(MachineVertex):
    """ Cell which represents a cell within the 2d fabric
    """

    def __init__(self, label):
        MachineVertex.__init__(self, label)

    @property
    def resources_required(self):
        return ResourceContainer()
