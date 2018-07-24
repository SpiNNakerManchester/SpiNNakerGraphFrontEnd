import logging

from pacman.executor.injection_decorator import inject_items
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_probeable import AbstractProbeable
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    NotProbeableException

logger = FormatAdapter(logging.getLogger(__name__))


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

    @inject_items({"operator_graph": "NengoOperatorGraph"})
    @overrides(
        AbstractNengoApplicationVertex.create_machine_vertices,
        additional_arguments="operator_graph")
    def create_machine_vertices(self, resource_tracker, operator_graph):
        pass
