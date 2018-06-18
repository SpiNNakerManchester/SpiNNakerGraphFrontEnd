from six import add_metaclass

from spinn_utilities.abstract_base import AbstractBase, abstractmethod
from spinnaker_graph_front_end.examples.nengo import constants


@add_metaclass(AbstractBase)
class AbstractTransmissionParameters(object):

    def __init__(self):
        pass

    @abstractmethod
    def __ne__(self, other):
        """
        
        :param other: 
        :return: 
        """

    @abstractmethod
    def __eq__(self, other):
        """
        
        :param other: 
        :return: 
        """

    @abstractmethod
    def __hash__(self):
        """
        
        :return: 
        """

    @abstractmethod
    def concat(self, other):
        """
        
        :param other: 
        :return: 
        """

    @abstractmethod
    def projects_to(self, space):
        """
        
        :param space: 
        :return: 
        """

    @abstractmethod
    def full_transform(self, slice_in=True, slice_out=True):
        """
        
        :param slice_in: 
        :param slice_out: 
        :return: 
        """
