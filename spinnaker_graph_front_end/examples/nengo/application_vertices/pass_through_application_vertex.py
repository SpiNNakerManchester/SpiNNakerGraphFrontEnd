from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex


class PassThroughApplicationVertex(AbstractNengoApplicationVertex):

    def __init__(self, label, rng):
        AbstractNengoApplicationVertex.__init__(self, label=label, rng=rng)

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        raise
