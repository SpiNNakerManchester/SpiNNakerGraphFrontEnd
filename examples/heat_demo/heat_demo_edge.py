from enum import Enum

# front end common imports
from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_edge import AbstractProvidesNKeysForEdge
from spinnaker_graph_front_end.models.\
    mutli_cast_partitioned_edge_with_n_keys import \
    MultiCastPartitionedEdgeWithNKeys


class HeatDemoEdge(MultiCastPartitionedEdgeWithNKeys,
                   AbstractProvidesNKeysForEdge):
    """ Used in conjunction with a heat demo vertex to execute the heat demo
    """

    DIRECTIONS = Enum(value="EDGES",
                      names=[("EAST", 0),
                             ("NORTH", 1),
                             ("WEST", 2),
                             ("SOUTH", 3)])

    def __init__(self, pre_subvertex, post_subvertex, direction, n_keys=1,
                 label=None, constraints=None):
        MultiCastPartitionedEdgeWithNKeys.__init__(
            self, pre_subvertex, post_subvertex, n_keys=n_keys, label=label,
            constraints=constraints)
        AbstractProvidesNKeysForEdge.__init__(self)
        self._direction = direction

    @property
    def direction(self):
        """

        :return:
        """
        return self._direction

    def get_n_keys_for_partition(self, partition, graph_mapper):
        """

        :param partition:
        :param graph_mapper:
        :return:
        """
        return 1

    def is_partitioned_edge(self):
        return True

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "HeatDemoedge:{}:{}:{}".format(self._label, self._direction,
                                              self._n_keys)
