from six import add_metaclass

from nengo.utils import numpy as nengo_numpy
from spinn_utilities.abstract_base import AbstractBase


@add_metaclass(AbstractBase)
class AbstractNengoObject(object):

    #__slots__ = ["_seed"]

    def __init__(self, rng, seed):
        if seed is None:
            self._seed = self.get_seed(rng)
        else:
            self._seed = seed

    @staticmethod
    def get_seed(rng):
        seed = rng.randint(nengo_numpy.maxint)
        return seed

    @property
    def seed(self):
        return self._seed
