from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import \
    ResourceContainer, CPUCyclesPerTickResource, DTCMResource, SDRAMResource


class SpaceTakerMachineVertex(MachineVertex):

    def __init__(self, x, y):
        super(SpaceTakerMachineVertex, self).__init__()
        self._x = x
        self._y = y

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def resources_required(self):
        resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100), sdram=SDRAMResource(100))
        return resources

    def __repr__(self):
        return "SpaceTakerVertex(x={}, y={})".format(self._x, self._y)
