from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_probeable import AbstractProbeable
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    NotProbeableException


class ValueSourceApplicationVertex(
        AbstractNengoApplicationVertex, AbstractProbeable):

    __slots__ = [
        #
        '_nengo_output_function',
        #
        '_size_out',
        #
        '_update_period',
        #
        '_recording_of'
    ]

    PROBEABLE_ATTRIBUTES = ['output']

    def __init__(
            self, label, rng, nengo_output_function, size_out, update_period):
        AbstractNengoApplicationVertex.__init__(self, label=label, rng=rng)
        self._nengo_output_function = nengo_output_function
        self._size_out = size_out
        self._update_period = update_period
        self._recording_of = dict()

        for attribute in self.PROBEABLE_ATTRIBUTES:
            self._recording_of[attribute] = False

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        pass

    @property
    def constraints(self):
        pass

    def add_constraint(self, constraint):
        pass

    def get_data_for_variable(self, variable):
        pass

    def can_probe_variable(self, variable):
        return variable in self._recording_of

    def set_probeable_variable(self, variable):
        if self.can_probe_variable(variable):
            self._recording_of[variable] = True
        else:
            raise NotProbeableException(
                "value source vertex does not support probing of"
                " variable {}".format(variable))
