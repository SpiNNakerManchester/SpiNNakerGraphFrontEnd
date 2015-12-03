"""
HeatDemoCommandEdge
"""
from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_edge import AbstractProvidesNKeysForEdge
from spinnaker_graph_front_end.models.\
    mutli_cast_partitioned_edge_with_n_keys import \
    MultiCastPartitionedEdgeWithNKeys


class HeatDemoCommandEdge(MultiCastPartitionedEdgeWithNKeys,
                          AbstractProvidesNKeysForEdge):
    """
    HeatDemoCommandEdge: an edge which is to send
    """

    def __init__(self, pre_subvertex, post_subvertex, n_keys,
                 label=None, constraints=None):
        MultiCastPartitionedEdgeWithNKeys.__init__(
            self, pre_subvertex, post_subvertex, n_keys, label, constraints)
        AbstractProvidesNKeysForEdge.__init__(self)