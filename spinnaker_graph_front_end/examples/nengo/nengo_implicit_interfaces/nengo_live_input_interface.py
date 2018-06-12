from six import add_metaclass

from spinn_utilities.abstract_base import AbstractBase, abstractmethod


@add_metaclass(AbstractBase)
class NengoLiveInputInterface(object):

    def __init__(self):
        pass

    @abstractmethod
    def output(self, t):
        """ enforced by the nengo duck typing
        
        :param t: 
        :return: 
        """
