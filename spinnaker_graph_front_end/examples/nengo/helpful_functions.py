from data_specification.enums import DataType
import numpy


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
