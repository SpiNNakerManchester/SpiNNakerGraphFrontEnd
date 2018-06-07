import numpy
try:
    from xxhash import xxh64 as fasthash
except ImportError:  # pragma: no cover
    from hashlib import md5 as fasthash
    import warnings
    warnings.warn("xxhash not installed, falling back to md5. "
                  "Install xxhash to improve build performance.", UserWarning)


class ParameterTransform(object):
    __slots__ = [
        #
        "_size_in",
        #
        "_size_out",
        #
        "_transform",
        #
        "_slice_in",
        #
        "_slice_out"]

    FLAGS_NAME = "WRITEABLE"

    def __init__(self, size_in, size_out, transform,
                 slice_in=slice(None), slice_out=slice(None)):
        self._size_in = size_in
        self._size_out = size_out

        # Transform the slices into an appropriate format
        self._slice_in = ParameterTransform._get_slice_as_ndarray(
            slice_in, size_in)
        self._slice_out = ParameterTransform._get_slice_as_ndarray(
            slice_out, size_out)

        # Copy the transform into a C-contiguous, read-only form
        self._transform = numpy.array(transform, order='C')
        self._transform.flags[self.FLAGS_NAME] = False

    @staticmethod
    def _get_slice_as_ndarray(sl, size):
        """Return a slice as a read-only Numpy array."""
        if isinstance(sl, slice):
            sl = numpy.array(range(size)[sl])
        else:
            sl = numpy.array(sorted(set(sl)))

        sl.flags[ParameterTransform.FLAGS_NAME] = False

        return sl

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return (self._size_in == other.size_in and
                self._size_out == other.size_out and
                numpy.array_equal(self._slice_in, other.slice_in) and
                numpy.array_equal(self._slice_out, other.slice_out) and
                numpy.array_equal(self._transform, other.transform))

    def __hash__(self):
        # The hash is combination of all the elements of the tuple, but we use
        # a faster hashing mechanism to hash the array types.
        return hash((self._size_in,
                     self._size_out,
                     fasthash(self._slice_in).hexdigest(),
                     fasthash(self._slice_out).hexdigest(),
                     fasthash(self._transform).hexdigest()))

    def full_transform(self, slice_in=True, slice_out=True):
        """Get an expanded form of the transform."""
        # Determine the shape of the resulting matrix
        size_in = len(self._slice_in) if slice_in else self._size_in
        size_out = len(self._slice_out) if slice_out else self._size_out

        # Get the slices
        columns = numpy.arange(size_in) if slice_in else numpy.array(
            self._slice_in)
        rows = numpy.arange(size_out) if slice_out else numpy.array(
            self._slice_out)

        # Prepare the transform
        transform = numpy.zeros((size_out, size_in))

        if self._transform.ndim < 2:
            # For vectors and scalars
            transform[rows, columns] = self._transform
        elif self._transform.ndim == 2:
            # For matrices
            rows_transform = numpy.zeros_like(transform[rows, :])
            rows_transform[:, columns] = self._transform
            transform[rows] = rows_transform
        else:  # pragma: no cover
            raise NotImplementedError

        return transform

    def projects_to(self, space):
        """Indicate whether the output of the connection described by the
        connection will intersect with the specified range of dimensions.
        """
        space = set(ParameterTransform._get_slice_as_ndarray(
            space, self._size_out))

        if self._transform.ndim == 0:
            outputs = set(self._slice_out)
        elif self._transform.ndim == 1:
            outputs = set(self._slice_out[self._transform != 0])
        elif self._transform.ndim == 2:
            outputs = set(self._slice_out[numpy.any(
                self._transform != 0, axis=1)])
        else:  # pragma: no cover
            raise NotImplementedError

        return len(outputs.intersection(space)) != 0

    @staticmethod
    def concat(a, b):
        """Return a transform which is the result of concatenating this
        transform with another.
        """
        assert a.size_out == b.size_in

        # Determine where the output dimensions of this transform and the input
        # dimensions of the other intersect.
        out_sel = numpy.zeros(a.size_out, dtype=bool)
        out_sel[a.slice_out] = True

        in_sel = numpy.zeros(b.size_in, dtype=bool)
        in_sel[b.slice_in] = True

        mid_sel = numpy.logical_and(out_sel, in_sel)

        # If the slices do not intersect at all then return None to indicate
        # that the connection will be empty.
        if not numpy.any(mid_sel):
            return None

        # If the first transform is specified with either a scalar or a vector
        # (as a diagonal) then the slice in is modified by `mid_sel'.
        slice_in_sel = mid_sel[a.slice_out]
        if a.transform.ndim < 2:
            # Get the new slice in
            slice_in = a.slice_in[slice_in_sel]

            # Get the new transform
            if a.transform.ndim == 0:
                a_transform = a.transform
            else:
                a_transform = a.transform[slice_in_sel]
        else:
            # The slice in remains the same but the rows of the transform are
            # sliced.
            slice_in = a.slice_in
            a_transform = a.transform[slice_in_sel]

        # If the second transform is specified with either a scalar or a vector
        # (as a diagonal) then the output slice is modified by `mid_sel'
        slice_out_sel = mid_sel[b.slice_in]
        if b.transform.ndim < 2:
            # Get the new slice out
            slice_out = b.slice_out[slice_out_sel]

            # Get the new transform
            if b.transform.ndim == 0:
                b_transform = b.transform
            else:
                b_transform = b.transform[slice_out_sel]
        else:
            # The slice out remains the same but the columns of the transform
            # are sliced.
            slice_out = b.slice_out
            b_transform = b.transform[:, slice_out_sel]

        # Multiply the transforms together
        if a_transform.ndim < 2 or b_transform.ndim == 0:
            new_transform = b_transform * a_transform
        elif b_transform.ndim == 1:
            new_transform = (b_transform * a_transform.T).T
        else:
            new_transform = numpy.dot(b_transform, a_transform)

        # If the transform is filled with zeros then return None
        if not numpy.any(new_transform != 0.0):
            return None

        # Create the new Transform
        return ParameterTransform(size_in=a.size_in, slice_in=slice_in,
                                  transform=new_transform,
                                  size_out=b.size_out, slice_out=slice_out)

    def hstack(self, other):
        """Create a new transform as the result of stacking this transform with
        another.
        """
        if self._size_out != other.size_out:
            raise ValueError(
                "Cannot horizontally stack two transforms with different "
                "output sizes ({} and {})".format(
                    self._size_out, other.size_out)
            )

        # Compute the new input size and the new input slice
        size_in = self._size_in + other.size_in
        slice_in = numpy.hstack(
            (self._slice_in, other.slice_in + self._size_in))

        # Determine which rows must be contained in the output matrix.
        slice_out = numpy.union1d(self._slice_out, other.slice_out)

        # Construct the new matrix
        n_rows = len(slice_out)
        n_cols = len(slice_in)
        matrix = numpy.zeros((n_rows, n_cols))

        # Write in the elements from our self, and then the elements from the
        # other matrix.
        offset = 0  # Used to perform the stacking
        for t in (self, other):
            # Select the rows which should be written
            selected_rows = numpy.array([i in t._slice_out for i in slice_out])
            rows = numpy.arange(n_rows)[selected_rows]

            # Select the columns to be written, note that the offset is used
            # for stacking.
            n_cols = len(t._slice_in)
            cols = numpy.arange(offset, offset + n_cols)
            offset += n_cols

            if t._transform.ndim < 2:
                # If the transform was specified as either a scalar or a
                # diagonal.
                matrix[rows, cols] = t._transform
            elif t._transform.ndim == 2:
                # If the transform is a matrix
                rows_transform = numpy.zeros_like(matrix[rows, :])
                rows_transform[:, cols] = t._transform
                matrix[rows] += rows_transform
            else:  # pragma: no cover
                raise NotImplementedError

        # Return the new transform
        return ParameterTransform(
            size_in, self._size_out, matrix, slice_in, slice_out)
