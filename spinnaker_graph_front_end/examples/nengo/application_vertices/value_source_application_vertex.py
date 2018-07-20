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
        #
        '_probeable_variables'
    ]

    PROBEABLE_ATTRIBUTES = ['output']

    def __init__(
            self, label, rng, nengo_output_function, size_out, update_period,
            utilise_extra_core_for_output_types_probe, seed):
        AbstractNengoApplicationVertex.__init__(
            self, label=label, rng=rng, seed=seed)
        self._nengo_output_function = nengo_output_function
        self._size_out = size_out
        self._update_period = update_period
        self._recording_of = dict()

        self._probeable_variables = dict()
        if not utilise_extra_core_for_output_types_probe:
            for attribute in self.PROBEABLE_ATTRIBUTES:
                self._recording_of[attribute] = False

    @property
    def nengo_output_function(self):
        return self._nengo_output_function

    @property
    def size_out(self):
        return self._size_out

    @property
    def update_period(self):
        return self._update_period

    @property
    def recording_of(self):
        return self._recording_of

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
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
