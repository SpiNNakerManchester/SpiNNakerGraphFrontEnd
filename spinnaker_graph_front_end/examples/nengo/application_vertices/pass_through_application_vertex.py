from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex


class PassThroughApplicationVertex(AbstractNengoApplicationVertex):

    __slots__ = []

    def __init__(self, label, rng):
        AbstractNengoApplicationVertex.__init__(self, label=label, rng=rng)

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        raise NotImplementedError(
            "This vertex has not been implemented. Please set the config "
            "param [Node] optimise_out_pass_through_nodes to True to avoid "
            "this error.")