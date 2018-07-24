import math

from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import helpful_functions
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.machine_vertices.\
    value_sink_machine_vertex import ValueSinkMachineVertex


class ValueSinkApplicationVertex(AbstractNengoApplicationVertex):

    __slots__ = [
        # the number of atoms this vertex is processing
        '_size_in'
    ]

    MAX_WIDTH = 16

    def __init__(self, label, rng, size_in, seed):
        AbstractNengoApplicationVertex.__init__(
            self, label=label, rng=rng, seed=seed)
        self._size_in = size_in

    @property
    def size_in(self):
        return self._size_in

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self, resource_tracker):
        # Make sufficient vertices to ensure that each has a size_in of less
        # than max_width.
        n_vertices = int(math.ceil((self._size_in // self.MAX_WIDTH)))

        vertices = list()
        for input_slice in helpful_functions.slice_up_atoms(
                self._size_in, n_vertices):
            vertices.append(ValueSinkMachineVertex(input_slice=input_slice))

        # Return the spec
        return vertices

