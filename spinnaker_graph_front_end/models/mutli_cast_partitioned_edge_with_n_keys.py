"""
MultiCastPartitionedEdgeWithNKeys
"""
from pacman.model.partitioned_graph.multi_cast_partitioned_edge import \
    MultiCastPartitionedEdge
from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_edge import \
    AbstractProvidesNKeysForEdge


class MultiCastPartitionedEdgeWithNKeys(MultiCastPartitionedEdge,
                                        AbstractProvidesNKeysForEdge):
    """
    MultiCastPartitionedEdgeWithNKeys: an partitioned edge which will use the
    multi cast fabric
    """

    def __init__(self, pre_subvertex, post_subvertex, n_keys, label=None,
                 constraints=None):
        MultiCastPartitionedEdge.__init__(
            self, pre_subvertex, post_subvertex, label=label,
            constraints=constraints)
        AbstractProvidesNKeysForEdge.__init__(self)
        self._n_keys = n_keys

    def get_n_keys_for_partitioned_edge(self, partitioned_edge, graph_mapper):
        """
        returns the number of keys per partitioned_edge
        :param partitioned_edge: the edge to consider
        :param graph_mapper: the graph mapper (could be none)
        :return: the numebr of keys this edge has
        """
        return self._n_keys

