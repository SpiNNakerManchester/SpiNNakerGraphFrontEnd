from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.graph_components.\
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex


class LIFApplicationVertex(BasicNengoApplicationVertex):

    def __init__(self, label, rng):
        BasicNengoApplicationVertex.__init__(self, label=label, rng=rng)

    @overrides(BasicNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        pass