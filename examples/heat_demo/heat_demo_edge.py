from enum import Enum

# front end common imports
from pacman.model.partitioned_graph.multi_cast_partitioned_edge \
    import MultiCastPartitionedEdge


class HeatDemoEdge(MultiCastPartitionedEdge):
    """ Used in conjunction with a heat demo vertex to execute the heat demo
    """

    DIRECTIONS = Enum(value="EDGES",
                      names=[("EAST", 0),
                             ("NORTH", 1),
                             ("WEST", 2),
                             ("SOUTH", 3)])

    def __init__(self, pre_subvertex, post_subvertex, direction, n_keys=1,
                 label=None):
        MultiCastPartitionedEdge.__init__(
            self, pre_subvertex, post_subvertex, label=label)
        self._direction = direction

    @property
    def direction(self):
        """

        :return:
        """
        return self._direction

    def is_partitioned_edge(self):
        return True

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "HeatDemoEdge:{}:{}".format(self._label, self._direction)
