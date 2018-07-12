class NengoException(Exception):
    """ Raised when the front end detects an error
    """
    pass


class ProbeableException(NengoException):
    """ Raised when there are not enough routing table entries
    """
    pass


class NotProbeableException(NengoException):
    """ Raised when a neuron model is asked to prove a variable it does not 
    support in being probed.
    """
    pass


class NeuronTypeConstructorNotFoundException(NengoException):
    """ raised when there's a neuron model which has no constructor in the 
    tools. 
    """
    pass


class MissingSpecialParameterException(NengoException):
    """ raised when a vertex expects a special param not provided by nengo but
    by the simulator and it isnt provided
    """
    pass


class NotLocatedProbableClass(NengoException):
    """ raised when there's a probe on something that's not an ensemble
    """


class NotBuildingPassThroughNodes(NengoException):
    """raised when trying to build a machine vertex pass through node. 
    expectation that either it'll be supported in future, or flag will 
    disappear"""


class NotAbleToBeConnectedToAsADestination(NengoException):
    """raised during partitioning when a machine vertex that is a destination
     of a connection doesnt inherit from the accepts multicast signals 
     interface"""


class NotConcatableTransmissionParameter(NengoException):
    """ raised when during interposers, a transmission parameter is asked to
    concat a transmission parameter which it cant accept."""