from six import add_metaclass

from spinn_utilities.abstract_base import AbstractBase, abstractmethod


@add_metaclass(AbstractBase)
class NengoLiveOutputInterface(object):
    def __init__(self):
        pass

    @abstractmethod
    def output(self, t, x):
        """ enforced by the nengo duck typing

        :param t: 
        :param x:
        :return: 
        """
