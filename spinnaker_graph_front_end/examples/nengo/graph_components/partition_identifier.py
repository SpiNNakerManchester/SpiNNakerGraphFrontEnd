

class PartitionIdentifier(object):

    __slots__ = [
        '_source_port',
        '_transmission_parameter',
        '_weight',
        '_latching_required'
    ]

    def __init__(
            self, source_port, transmission_parameter, weight,
            latching_required):
        self._source_port = source_port
        self._transmission_parameter = transmission_parameter
        self._weight = weight
        self._latching_required = latching_required

    @property
    def transmission_parameter(self):
        return self._transmission_parameter

    @property
    def latching_required(self):
        return self._latching_required

    @property
    def weight(self):
        return self._weight

    @property
    def source_port(self):
        return self._source_port

    def __eq__(self, other):
        if isinstance(other, PartitionIdentifier):
            return (self._transmission_parameter == other.transmission_parameter
                    and self._latching_required == other.latching_required and
                    self._weight == other.weight and
                    self._source_port == other._source_port)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(
            (self._transmission_parameter, self._source_port,
             self._weight, self._latching_required))
