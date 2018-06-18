from six import add_metaclass

from spinn_utilities.abstract_base import AbstractBase


@add_metaclass(AbstractBase)
class AbstractConnectionApplicationDataHolder(object):

    __slots__ = [
        #
        '_transmission_params',
        #
        '_reception_params',
        #
        '_latching_required',
        #
        '_weight',
        #
        '_source_output_port',
        #
        '_destination_input_port'
    ]

    def __init__(self):
        self._transmission_params = None
        self._reception_params = None
        self._latching_required = None
        self._weight = None
        self._source_output_port = None
        self._destination_input_port = None

    def set_all_parameters(
            self, transmission_params, reception_params, latching_required,
            weight, source_output_port, destination_input_port):
        self._transmission_params = transmission_params
        self._reception_params = reception_params
        self._latching_required = latching_required
        self._weight = weight
        self._source_output_port = source_output_port
        self._destination_input_port = destination_input_port

    @property
    def transmission_params(self):
        return self._transmission_params

    @property
    def reception_params(self):
        return self._reception_params

    @property
    def latching_required(self):
        return self._latching_required

    @property
    def weight(self):
        return self._weight

    @property
    def source_output_port(self):
        return self._source_output_port

    @property
    def destination_input_port(self):
        return self._destination_input_port
