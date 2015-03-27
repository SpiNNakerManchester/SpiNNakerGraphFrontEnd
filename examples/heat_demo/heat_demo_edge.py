"""
HeatDemoEdge: used in conjunction with a heat demo vertex to execute the
heat demo
"""
from enum import Enum
from pacman.model.partitioned_graph.partitioned_edge import PartitionedEdge
# TODO remove this dependency
from spynnaker.pyNN.models.abstract_models.\
    abstract_provides_n_keys_for_edge import AbstractProvidesNKeysForEdge


class HeatDemoEdge(PartitionedEdge, AbstractProvidesNKeysForEdge):
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
        AbstractProvidesNKeysForEdge.__init__(self)
        self._direction = direction

    @property
    def direction(self):
        """

        :return:
        """
        return self._direction

    def get_n_keys_for_partitioned_edge(self, partitioned_edge, graph_mapper):
        """

        :param partitioned_edge:
        :param graph_mapper:
        :return:
        """
        return 1