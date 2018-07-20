from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.abstract_filter import \
    AbstractFilter


class NoneFilter(AbstractFilter):

    __slots__ = []

    def __init__(self, width, latching):
        AbstractFilter.__init__(self, width, latching)

    @overrides(AbstractFilter.__eq__)
    def __eq__(self, other):
        return (isinstance(other, NoneFilter) and
                self._width == other.width and
                self._latching == other.latching)

    @overrides(AbstractFilter.size_words)
    def size_words(self):
        return 0

    @overrides(AbstractFilter.pack_into)
    def pack_into(self, spec, dt):
        pass
