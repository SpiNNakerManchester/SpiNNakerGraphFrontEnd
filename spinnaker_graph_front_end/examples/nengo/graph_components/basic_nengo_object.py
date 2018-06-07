from nengo.utils import numpy as nengo_numpy


class BasicNengoObject(object):

    def __init__(self):
        pass

    @staticmethod
    def get_seed(obj, rng):
        seed = rng.randint(nengo_numpy.maxint)
        return seed if getattr(obj, "seed", None) is None else obj.seed
