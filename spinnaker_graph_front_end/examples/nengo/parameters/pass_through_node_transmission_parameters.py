from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.parameters. \
    abstract_transmission_parameters import AbstractTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.parameters. \
    transmission_parameters_impl import TransmissionParametersImpl
from spinnaker_graph_front_end.examples.nengo.utility_objects.parameter_transform import \
    ParameterTransform


class PassthroughNodeTransmissionParameters(
        TransmissionParametersImpl, AbstractTransmissionParameters):
    """Parameters describing information transmitted by a passthrough node.
    """

    __slots__ = []

    def __init__(self, transform):
        AbstractTransmissionParameters.__init__(self)
        TransmissionParametersImpl.__init__(self, transform)

    @overrides(AbstractTransmissionParameters.concat)
    def concat(self, other):
        """Create new connection parameters which are the result of
        concatenating this connection several others.

        Parameters
        ----------
        other : PassthroughNodeTransmissionParameters
            Connection parameters to add to the end of this connection.

        Returns
        -------
        PassthroughNodeTransmissionParameters or None
            Either a new set of transmission parameters, or None if the
            resulting transform contained no non-zero values.
        """
        # Combine the transforms
        new_transform = self._transform.concat(other._transform)

        # Create a new connection (unless the resulting transform is empty,
        # in which case don't)
        if new_transform is not None:
            return PassthroughNodeTransmissionParameters(new_transform)
        else:
            # The transform consisted entirely of zeros so return None.
            return None

    def hstack(self, *others):
        """Create new connection parameters which are the result of stacking
        these connection parameters with other connection parameters.

        Parameters
        ----------
        *others : PassthroughNodeTransmissionParameters
            Additional connection parameters to stack against these parameters.

        Returns
        -------
        PassthroughNodeTransmissionParameters
            A new set of transmission parameters resulting from stacking the
            provided parameters together.
        """
        # Horizontally stack the parameters
        stacked_transform = self._transform
        for other in others:
            stacked_transform = stacked_transform.hstack(other._transform)

        # Create and return the new connection
        return PassthroughNodeTransmissionParameters(stacked_transform)

    @property
    @overrides(TransmissionParametersImpl.as_global_inhibition_connection)
    def as_global_inhibition_connection(self):
        """Construct a copy of the connection with the optimisation for global
        inhibition applied.
        """
        assert self.supports_global_inhibition
        transform = self.full_transform(slice_out=False)[0, :]

        return PassthroughNodeTransmissionParameters(
            ParameterTransform(
                size_in=self.size_in, size_out=1, transform=transform,
                slice_in=self.slice_in))
