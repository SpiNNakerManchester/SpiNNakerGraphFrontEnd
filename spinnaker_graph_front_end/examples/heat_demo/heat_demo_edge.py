from enum import Enum
from pacman.model.graphs.machine import MachineEdge


class HeatDemoEdge(MachineEdge):
    """ Used in conjunction with a heat demo vertex to execute the heat demo
    """

    DIRECTIONS = Enum(value="EDGES",
                      names=[("EAST", 0),
                             ("NORTH", 1),
                             ("WEST", 2),
                             ("SOUTH", 3)])

    def __init__(self, pre_vertex, post_vertex, direction, n_keys=1,
                 label=None):
        MachineEdge.__init__(
            self, pre_vertex, post_vertex, label=label)
        self._direction = direction

    @property
    def direction(self):
        """

        :return:
        """
        return self._direction

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "HeatDemoEdge:{}:{}".format(self.label, self._direction)
