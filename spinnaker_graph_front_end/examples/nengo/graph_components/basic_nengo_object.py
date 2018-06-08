from six import add_metaclass

from nengo.utils import numpy as nengo_numpy
from spinn_utilities.abstract_base import AbstractBase


@add_metaclass(AbstractBase)
class BasicNengoObject(object):

    def __init__(self, rng):
        self._seed = self._get_seed(rng)

    @staticmethod
    def _get_seed(rng):
        seed = rng.randint(nengo_numpy.maxint)
        return seed

    @property
    def seed(self):
        return self._seed
