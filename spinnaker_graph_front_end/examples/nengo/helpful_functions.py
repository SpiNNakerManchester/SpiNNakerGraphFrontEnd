from data_specification.enums import DataType
import numpy

from pacman.model.graphs.common import Slice


def get_seed(nengo_object):
    if hasattr(nengo_object, "seed"):
        return nengo_object.seed
    else:
        return None


def convert_numpy_array_to_s16_15(values):
    """Convert the given NumPy array of values into fixed point format."""
    # Scale and cast to appropriate int types
    scaled_values = values * DataType.S1615.scale

    # Saturate the values
    clipped_values = numpy.clip(scaled_values, DataType.S1615.min,
                                DataType.S1615.max)

    # **NOTE** for some reason just casting resulted in shape
    # being zeroed on some indeterminate selection of OSes,
    # architectures, Python and Numpy versions"
    return numpy.array(clipped_values, copy=True, dtype=numpy.int32)


def slice_up_atoms(initial_slice, n_slices):
    """Create a set of smaller slices from an original slice.
    
    :param initial_slice: A slice which must have `start` and `stop` set.
    :type initial_slice: :py:class:`slice`
    :param n_slices:  Number of slices to produce.
    :type n_slices: int
    :rtype: Iterator[:py:class:`pacman.model.graphs.common.Slice`]  
    """

    # Extract current position, start and stop
    pos = start = initial_slice.start
    stop = initial_slice.stop

    # Determine the chunk sizes
    chunk = (stop - start) // n_slices
    n_larger = (stop - start) % n_slices

    # Yield the larger slices
    for _ in range(n_larger):
        yield Slice(pos, pos + chunk + 1)
        pos += chunk + 1

    # Yield the standard sized slices
    for _ in range(n_slices - n_larger):
        yield Slice(pos, pos + chunk)
        pos += chunk
