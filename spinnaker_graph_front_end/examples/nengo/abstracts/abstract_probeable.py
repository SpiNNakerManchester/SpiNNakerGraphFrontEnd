from six import add_metaclass

from spinn_utilities.abstract_base import AbstractBase, abstractmethod


@add_metaclass(AbstractBase)
class AbstractProbeable(object):

    __slots__ = []

    def __init__(self):
        pass

    @abstractmethod
    def can_probe_variable(self, variable):
        """
        
        :param variable: 
        :return: 
        """

    @abstractmethod
    def set_probeable_variable(self, variable):
        """
        
        :param variable: 
        :return: 
        """

    @abstractmethod
    def get_data_for_variable(self, variable):
        """
        
        :param variable: 
        :return: 
        """