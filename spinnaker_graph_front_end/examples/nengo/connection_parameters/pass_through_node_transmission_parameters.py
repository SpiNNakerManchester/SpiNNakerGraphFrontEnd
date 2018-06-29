from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    abstract_transmission_parameters import AbstractTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters. \
    transmission_parameters_impl import TransmissionParametersImpl
from spinnaker_graph_front_end.examples.nengo.utility_objects.\
    parameter_transform import ParameterTransform


class PassthroughNodeTransmissionParameters(
        TransmissionParametersImpl, AbstractTransmissionParameters):
    """Parameters describing information transmitted by a passthrough node.
    """

    __slots__ = []

    def __init__(self, transform):
        AbstractTransmissionParameters.__init__(self)
        TransmissionParametersImpl.__init__(self, transform)

    def __repr__(self):
        return "{}".format(self._transform)

    def __str__(self):
        return self.__repr__()

    @overrides(AbstractTransmissionParameters.concat)
    def concat(self, other):
        """Create new connection connection_parameters which are the result of
        concatenating this connection several others.

        Parameters
        ----------
        other : PassthroughNodeTransmissionParameters
            Connection connection_parameters to add to the end of this connection.

        Returns
        -------
        PassthroughNodeTransmissionParameters or None
            Either a new set of transmission connection_parameters, or None if the
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
        """Create new connection connection_parameters which are the result of stacking
        these connection connection_parameters with other connection connection_parameters.

        Parameters
        ----------
        *others : PassthroughNodeTransmissionParameters
            Additional connection connection_parameters to stack against these connection_parameters.

        Returns
        -------
        PassthroughNodeTransmissionParameters
            A new set of transmission connection_parameters resulting from stacking the
            provided connection_parameters together.
        """
        # Horizontally stack the connection_parameters
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
