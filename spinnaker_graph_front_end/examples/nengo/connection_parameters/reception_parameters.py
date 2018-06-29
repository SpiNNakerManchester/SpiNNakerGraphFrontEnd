import numpy
from nengo import LinearFilter


class ReceptionParameters(object):
    """Basic reception connection_parameters that relate to the reception of a series of
    multicast packets.

    Attributes
    ----------
    parameter_filter : :py:class:`~nengo.synapses.Synapse`
        Synaptic filter which should be applied to received values.
    width : int
        Width of the post object
    """

    def __init__(self, parameter_filter, width, learning_rule):
        self._parameter_filter = parameter_filter
        self._width = width
        self._learning_rule = learning_rule

    def __repr__(self):
        return "{}:{}:{}".format(self._parameter_filter, self._width,
                                 self._learning_rule)
    def __str__(self):
        return self.__repr__()

    @property
    def parameter_filter(self):
        return self._parameter_filter

    @property
    def width(self):
        return self._width

    @property
    def learning_rule(self):
        return self._learning_rule

    def concat(self, other):
        """Create new reception connection_parameters by combining this set of reception
        connection_parameters with another.
        """
        # Combine the filters
        if self._parameter_filter is None:
            new_filter = other.filter
        elif other.filter is None:
            new_filter = self._parameter_filter
        elif (isinstance(self._parameter_filter, LinearFilter) and
                isinstance(other.parameter_filter, LinearFilter)):
            # Combine linear filters by multiplying their numerators and
            # denominators.
            new_filter = LinearFilter(
                numpy.polymul(self._parameter_filter.num,
                              other.parameter_filter.num),
                numpy.polymul(self._parameter_filter.den,
                              other.parameter_filter.den)
            )
        else:
            raise NotImplementedError(
                "Cannot combine filters of type {} and {}".format(
                    type(self._parameter_filter), type(other.filter)))

        # Combine the learning rules
        if self._learning_rule is not None and other.learning_rule is not None:
            raise NotImplementedError(
                "Cannot combine learning rules {} and {}".format(
                    self._learning_rule, other.learning_rule))

        new_learning_rule = self._learning_rule or other.learning_rule

        # Create the new reception connection_parameters
        return ReceptionParameters(new_filter, other.width, new_learning_rule)
