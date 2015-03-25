"""
HeatDemoEdge: used in conjunction with a heat demo vertex to execute the
heat demo
"""
from enum import Enum
from pacman.model.partitionable_graph.partitionable_edge import \
    PartitionableEdge


class HeatDemoEdge(PartitionableEdge):
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
        PartitionableEdge.__init__(self, pre_vertex, post_vertex, label,
                                   constraints)
        self._direction = direction

    @property
    def direction(self):
        return self._direction