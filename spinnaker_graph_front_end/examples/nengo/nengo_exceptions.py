class NengoException(Exception):
    """ Raised when the front end detects an error
    """
    pass


class ProbeableException(NengoException):
    """ Raised when there are not enough routing table entries
    """
    pass


class NeuronTypeConstructorNotFoundException(NengoException):
    """ raised when there's a neuron model which has no constructor in the 
    tools. 
    """
    pass


class NotLocatedProbableClass(NengoException):
    """ raised when there's a probe on something that's not an ensemble
    """


class NotBuildingPassThroughNodes(NengoException):
    """raised when trying to build a machine vertex pass through node. 
    expectation that either it'll be supported in future, or flag will 
    disappear"""

