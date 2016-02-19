
from pacman.model.routing_info.dict_based_partitioned_edge_n_keys_map import \
    DictBasedPartitionedEdgeNKeysMap
from spinn_front_end_common.abstract_models.\
    abstract_provides_incoming_partition_constraints import \
    AbstractProvidesIncomingPartitionConstraints
from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_partition import \
    AbstractProvidesNKeysForPartition
from spinn_front_end_common.abstract_models.\
    abstract_provides_outgoing_partition_constraints import \
    AbstractProvidesOutgoingPartitionConstraints


class SpinnakerGraphFrontEndEdgeToKeyMapper(object):

    def __call__(self, partitioned_graph, partitionable_graph=None,
                 graph_mapper=None):

        # Generate an n_keys map for the graph and add constraints
        n_keys_map = DictBasedPartitionedEdgeNKeysMap()
        if partitionable_graph is not None and graph_mapper is not None:

            for edge in partitioned_graph.subedges:
                vertex_slice = graph_mapper.get_subvertex_slice(
                    edge.pre_subvertex)
                super_edge = graph_mapper\
                    .get_partitionable_edge_from_partitioned_edge(edge)

                if not isinstance(super_edge.pre_vertex,
                                  AbstractProvidesNKeysForPartition):
                    n_keys_map.\
                        set_n_keys_for_patitioned_edge(edge,
                                                       vertex_slice.n_atoms)
                else:
                    n_keys_map.set_n_keys_for_patitioned_edge(
                        edge,
                        super_edge.pre_vertex.get_n_keys_for_partition(
                            edge, graph_mapper))

                if isinstance(super_edge.pre_vertex,
                              AbstractProvidesOutgoingPartitionConstraints):
                    edge.add_constraints(
                        super_edge.pre_vertex.get_outgoing_edge_constraints(
                            edge, graph_mapper))
                if isinstance(super_edge.post_vertex,
                              AbstractProvidesIncomingPartitionConstraints):
                    edge.add_constraints(
                        super_edge.post_vertex.get_incoming_edge_constraints(
                            edge, graph_mapper))
        else:
            for edge in partitioned_graph.subedges:
                if not isinstance(edge.pre_subvertex,
                                  AbstractProvidesNKeysForEdge):
                    n_keys_map.set_n_keys_for_patitioned_edge(edge, 1)
                else:
                    n_keys_map.set_n_keys_for_patitioned_edge(
                        edge,
                        edge.pre_subvertex.get_n_keys_for_partition(
                            edge, graph_mapper))

                if isinstance(edge, AbstractProvidesNKeysForEdge):
                        n_keys = edge.get_n_keys_for_partition(edge,
                                                               graph_mapper)
                        n_keys_map.set_n_keys_for_patition(partition, n_keys)

                if isinstance(edge.pre_subvertex,
                              AbstractProvidesOutgoingEdgeConstraints):
                    edge.add_constraints(
                        edge.pre_subvertex.get_outgoing_edge_constraints(
                            edge, graph_mapper))
                if isinstance(edge.post_subvertex,
                              AbstractProvidesIncomingEdgeConstraints):
                    edge.add_constraints(
                        edge.post_subvertex.get_incoming_edge_constraints(
                            edge, graph_mapper))

        return {'n_keys_map': n_keys_map}
