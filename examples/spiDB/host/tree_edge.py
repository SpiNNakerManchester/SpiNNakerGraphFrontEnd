from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_edge import AbstractProvidesNKeysForEdge
from spynnaker_graph_front_end.models.\
    mutli_cast_partitioned_edge_with_n_keys import \
    MultiCastPartitionedEdgeWithNKeys

class TreeEdge(MultiCastPartitionedEdgeWithNKeys,AbstractProvidesNKeysForEdge):

    def __init__(self, pre_subvertex, post_subvertex, n_keys=1,
                 label=None, constraints=None):
        MultiCastPartitionedEdgeWithNKeys.__init__(
            self, pre_subvertex, post_subvertex, n_keys=n_keys, label=label,
            constraints=constraints)
        AbstractProvidesNKeysForEdge.__init__(self)

    def get_n_keys_for_partitioned_edge(self, partitioned_edge, graph_mapper):
        return 1

    def is_partitioned_edge(self):
        return True

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "TreeEdge:{}"\
            .format(self._label)