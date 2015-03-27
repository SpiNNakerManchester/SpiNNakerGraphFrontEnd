"""
HeatDemoEdge: used in conjunction with a heat demo vertex to execute the
heat demo
"""
from enum import Enum
from pacman.model.partitioned_graph.partitioned_edge import PartitionedEdge


class HeatDemoEdge(PartitionedEdge):
    """
    HeatDemoEdge: used in conjunction with a heat demo vertex to execute the
    heat demo
    """

    DIRECTIONS = Enum(value="EDGES",
                      names=[("EAST", 0),
                             ("NORTH_EAST", 1),
                             ("NORTH", 2),
                             ("WEST", 3),
                             ("SOUTH_WEST", 4),
                             ("SOUTH", 5)])

    def __init__(self, pre_vertex, post_vertex, direction, label, constraints):
        PartitionedEdge.__init__(self, pre_vertex, post_vertex, constraints,
                                 label)
        self._direction = direction

    @property
    def direction(self):
        """

        :return:
        """
        return self._direction