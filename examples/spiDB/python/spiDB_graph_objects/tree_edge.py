from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_partition import \
    AbstractProvidesNKeysForPartition
from pacman.model.partitioned_graph.multi_cast_partitioned_edge \
    import MultiCastPartitionedEdge


class TreeEdge(MultiCastPartitionedEdge, AbstractProvidesNKeysForPartition):

    def __init__(self, pre_subvertex, post_subvertex, label=None):
        MultiCastPartitionedEdge.__init__(
            self, pre_subvertex, post_subvertex, label=label)
        AbstractProvidesNKeysForPartition.__init__(self)
        
    def get_n_keys_for_partition(self, partition, graph_mapper):
        return 1

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "TreeEdge:{}"\
            .format(self._label)