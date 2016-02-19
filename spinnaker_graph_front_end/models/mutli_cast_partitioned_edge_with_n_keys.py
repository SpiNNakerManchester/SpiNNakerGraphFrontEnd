from pacman.model.partitioned_graph.multi_cast_partitioned_edge import \
    MultiCastPartitionedEdge
from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_partition import \
    AbstractProvidesNKeysForPartition


class MultiCastPartitionedEdgeWithNKeys(MultiCastPartitionedEdge,
                                        AbstractProvidesNKeysForPartition):
    """ A partitioned edge which will use the multicast fabric
    """

    def __init__(self, pre_subvertex, post_subvertex, n_keys, label=None,
                 constraints=None):
        MultiCastPartitionedEdge.__init__(
            self, pre_subvertex, post_subvertex, label=label,
            constraints=constraints)
        AbstractProvidesNKeysForPartition.__init__(self)
        self._n_keys = n_keys

    def get_n_keys_for_partition(self, partition, graph_mapper):
        """ Get the number of keys per partitioned_edge

        :param partition: the outgoing partition to consider
        :param graph_mapper: the graph mapper (could be none)
        :return: the number of keys this edge has
        """
        return self._n_keys
