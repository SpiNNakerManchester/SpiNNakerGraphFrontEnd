from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.graph_components. \
    basic_nengo_application_vertex import \
    BasicNengoApplicationVertex


class ValueSourceApplicationVertex(BasicNengoApplicationVertex):
    def __init__(self, label, rng, nengo_node_output, nengo_node_size_out,
                 period):
        BasicNengoApplicationVertex.__init__(self, label=label, rng=rng)
        self._nengo_node_output = nengo_node_output
        self._nengo_node_size_out = nengo_node_size_out
        self._period = period

    @overrides(BasicNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        pass
