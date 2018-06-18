import numpy

from spinnaker_graph_front_end.examples.nengo import constants


class TransmissionParametersImpl(object):
    __slots__ = ["_transform"]

    def __init__(self, transform):
        # Store the transform
        self._transform = transform

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return (type(self) is type(other) and
                self._transform == other._transform)

    def __hash__(self):
        return hash((type(self), self._transform))

    def full_transform(self, slice_in=True, slice_out=True):
        return self._transform.full_transform(slice_in, slice_out)

    def projects_to(self, space):
        return self._transform.projects_to(space)

    @property
    def supports_global_inhibition(self):
        """Indicates whether this transform supports being optimised out as a
        global inhibition connection.
        """
        # True iff. every row of the transform is the same
        transform = self.full_transform(slice_out=False)
        return numpy.all(transform[0, :] == transform[1:, :])

    @property
    def as_global_inhibition_connection(self):  # pragma: no cover
        raise NotImplementedError

    @property
    def transform(self):
        return self._transform

    def update_to_global_inhibition_if_required(self, destination_input_port):
        # change to support global inhibition if required
        if (destination_input_port is constants.ENSEMBLE_INPUT_PORT.NEURONS
                and self.supports_global_inhibition):
            destination_input_port = (
                constants.ENSEMBLE_INPUT_PORT.GLOBAL_INHIBITION)
            return self.as_global_inhibition_connection, destination_input_port
        else:
            return self, destination_input_port
