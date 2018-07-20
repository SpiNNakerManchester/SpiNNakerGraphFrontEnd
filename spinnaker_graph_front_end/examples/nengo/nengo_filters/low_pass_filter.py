from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import helpful_functions
from spinnaker_graph_front_end.examples.nengo.abstracts.abstract_filter import \
    AbstractFilter
import numpy


class LowPassFilter(AbstractFilter):

    __slots__ = [
        #
        '_time_constant'
    ]

    SIZE_OF_WORDS = 2
    FIXED_TIME_CONSTANT = 0.0
    SECOND_CO_EFFICIENT = 1.0

    def __init__(self, width, latching, time_constant):
        AbstractFilter.__init__(self, width, latching)
        self._time_constant = time_constant

    @property
    def time_constant(self):
        return self._time_constant

    @overrides(AbstractFilter.__eq__)
    def __eq__(self, other):
        return (isinstance(other, LowPassFilter) and
                self._width == other.width and
                self._latching == other.latching and
                self._time_constant == other.time_constant)

    @overrides(AbstractFilter.size_words)
    def size_words(self):
        return self.SIZE_OF_WORDS

    @overrides(AbstractFilter.pack_into)
    def pack_into(self, spec, dt):

        """Pack the struct describing the filter into the buffer."""
        # Compute the coefficients
        if self.time_constant != self.FIXED_TIME_CONSTANT:
            a = numpy.exp(-dt / self.time_constant)
        else:
            a = self.FIXED_TIME_CONSTANT

        b = self.SECOND_CO_EFFICIENT - a

        spec.write_value(helpful_functions.convert_numpy_array_to_s16_15(a))
        spec.write_value(helpful_functions.convert_numpy_array_to_s16_15(b))
