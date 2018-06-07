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
    """ raised when theres a probe on something thats not an ensemble
    """
