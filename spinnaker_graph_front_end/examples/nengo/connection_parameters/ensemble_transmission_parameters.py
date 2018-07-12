import numpy

from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    abstract_transmission_parameters import AbstractTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters.pass_through_node_transmission_parameters import \
    PassthroughNodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    transmission_parameters_impl import TransmissionParametersImpl
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    NotConcatableTransmissionParameter
from spinnaker_graph_front_end.examples.nengo.utility_objects\
    .parameter_transform import ParameterTransform

try:
    from xxhash import xxh64 as fasthash
except ImportError:  # pragma: no cover
    from hashlib import md5 as fasthash
    import warnings
    warnings.warn("xxhash not installed, falling back to md5. "
                  "Install xxhash to improve build performance.", UserWarning)


class EnsembleTransmissionParameters(
        TransmissionParametersImpl, AbstractTransmissionParameters):
    """Parameters describing information transmitted by an ensemble.

    Attributes
    ----------
    decoders : ndarray
        A matrix describing a decoding of the ensemble (sized N x D).
    learning_rule :
        Learning rule associated with the decoding.
    """

    __slots__ = [
        #
        "_decoders",
        #
        "_learning_rule"]

    def __init__(self, decoders, transform, learning_rule=None):
        AbstractTransmissionParameters.__init__(self)
        TransmissionParametersImpl.__init__(self, transform)

        # Copy the decoders into a C-contiguous, read-only array
        self._decoders = numpy.array(decoders, order='C')
        self._decoders.flags[transform.FLAGS_NAME] = False

        # Store the learning rule
        self._learning_rule = learning_rule

    def __repr__(self):
        return "{}:{}:{}".format(
            self._transform, self._decoders, self._learning_rule)

    def __str__(self):
        return self.__repr__()

    @property
    def decoders(self):
        return self._decoders

    @property
    def learning_rule(self):
        return self._learning_rule

    @overrides(TransmissionParametersImpl.__eq__)
    def __eq__(self, other):
        # Two connection_parameters are equal only if they are of the same
        #  type, and are equivalent in all other
        # fields.
        return (super(EnsembleTransmissionParameters, self).__eq__(other) and
                numpy.array_equal(self._decoders, other.decoders) and
                self._learning_rule == other.learning_rule)

    @overrides(TransmissionParametersImpl.__hash__)
    def __hash__(self):
        return hash((type(self), self._learning_rule, self._transform,
                     fasthash(self._decoders).hexdigest()))

    @overrides(AbstractTransmissionParameters.concat)
    def concat(self, other):
        """Create new connection connection_parameters which are the result of
        concatenating this connection with others.

        Parameters
        ----------
        other : PassthroughNodeTransmissionParameters
            Connection connection_parameters to add to the end of this connection.

        Returns
        -------
        EnsembleTransmissionParameters or None
            Either a new set of transmission connection_parameters, or None if the
            resulting transform contained no non-zero values.
        """

        if not isinstance(other, PassthroughNodeTransmissionParameters):
            raise NotConcatableTransmissionParameter()

        # Get the outgoing transformation
        new_transform = self._transform.concat(other.transform)

        # Create a new connection (unless the resulting transform is empty,
        # in which case don't)
        if new_transform is not None:
            return EnsembleTransmissionParameters(
                self._decoders, new_transform, self._learning_rule
            )
        else:
            # The transform consisted entirely of zeros so return None.
            return None

    @property
    @overrides(TransmissionParametersImpl.as_global_inhibition_connection)
    def as_global_inhibition_connection(self):
        """Construct a copy of the connection with the optimisation for global
        inhibition applied.
        """
        assert self.supports_global_inhibition
        transform = self.full_transform(slice_out=False)[0, :]

        return EnsembleTransmissionParameters(
            self._decoders,
            ParameterTransform(
                size_in=self._decoders.shape[0], size_out=1,
                transform=transform, slice_in=self._transform.slice_in)
        )

    @property
    def full_decoders(self):
        """Get the matrix corresponding to a combination of the decoders and
        the transform applied by the connection.
        """
        return numpy.dot(self.full_transform(slice_in=False, slice_out=False),
                         self._decoders)
