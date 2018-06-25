import numpy

import nengo
from nengo import builder as nengo_builder
from nengo.builder import ensemble
from nengo.utils import numpy as nengo_numpy
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_probeable import AbstractProbeable


class LIFApplicationVertex(
        AbstractNengoApplicationVertex, AbstractProbeable):

    __slots__ = [
        "_eval_points",
        "_encoders",
        "_scaled_encoders",
        "_max_rates",
        "_intercepts",
        "_gain",
        "_bias",
        "_probeable_variables",
        "_is_recording_probeable_variable",
        "_probeable_variables_supported_elsewhere"]

    def __init__(
            self, label, rng, seed, eval_points, encoders, scaled_encoders,
            max_rates, intercepts, gain, bias,
            utilise_extra_core_for_output_types_probe):
        """ constructor for lifs
        
        :param label: label of the vertex
        :param rng: random number generator
        :param eval_points: ????
        :param encoders: ????
        :param scaled_encoders: ??? 
        :param max_rates: ????
        :param intercepts: ????
        :param gain: ????
        :param bias: ????
        """
        AbstractNengoApplicationVertex.__init__(
            self, label=label, rng=rng, seed=seed)
        self._eval_points = eval_points
        self._encoders = encoders
        self._scaled_encoders = scaled_encoders
        self._max_rates = max_rates
        self._intercepts = intercepts
        self._gain = gain
        self._bias = bias

        self._probeable_variables = [
            constants.RECORD_OUTPUT_FLAG, constants.RECORD_SPIKES_FLAG,
            constants.RECORD_VOLTAGE_FLAG, constants.SCALED_ENCODERS_FLAG]

        self._is_recording_probeable_variable = dict()
        for flag in self._probeable_variables:
            self._is_recording_probeable_variable[flag] = False

        if not utilise_extra_core_for_output_types_probe:
            self._probeable_variables.append(
                constants.DECODER_OUTPUT_FLAG)
            self._is_recording_probeable_variable[
                constants.DECODER_OUTPUT_FLAG] = False

    @property
    def constraints(self):
        return []

    def add_constraint(self, constraint):
        pass

    @property
    def eval_points(self):
        return self._eval_points

    @property
    def encoders(self):
        return self._encoders

    @property
    def scaled_encoders(self):
        return self._scaled_encoders

    @property
    def max_rates(self):
        return self._max_rates

    @property
    def intercepts(self):
        return self._intercepts

    @property
    def gain(self):
        return self._gain

    @property
    def bias(self):
        return self._bias

    @overrides(AbstractProbeable.set_probeable_variable)
    def set_probeable_variable(self, variable):
        self._is_recording_probeable_variable[variable] = True

    @overrides(AbstractProbeable.get_data_for_variable)
    def get_data_for_variable(self, variable):
        pass

    @overrides(AbstractProbeable.can_probe_variable)
    def can_probe_variable(self, variable):
            if variable in self._probeable_variables:
                return True
            else:
                return False

    @staticmethod
    def generate_parameters_from_ensemble(
            nengo_ensemble, random_number_generator):
        """ goes through the nengo ensemble object and extracts the 
        connection_parameters for the lif neurons
        
        :param nengo_ensemble: the ensemble handed down by nengo
        :param random_number_generator: the random number generator 
        controlling all random in this nengo run
        :return: dict of params with names.
        """
        eval_points = nengo_builder.ensemble.gen_eval_points(
            nengo_ensemble, nengo_ensemble.eval_points,
            rng=random_number_generator)

        # Get the encoders
        if isinstance(nengo_ensemble.encoders, nengo.dists.Distribution):
            encoders = nengo_ensemble.encoders.sample(
                nengo_ensemble.n_neurons, nengo_ensemble.dimensions,
                rng=random_number_generator)
            encoders = numpy.asarray(encoders, dtype=numpy.float64)
        else:
            encoders = nengo_numpy.array(
                nengo_ensemble.encoders, min_dims=2, dtype=numpy.float64)
        encoders /= nengo_numpy.norm(encoders, axis=1, keepdims=True)

        # Get correct sample function (seems dists.get_samples not in nengo
        # dists in some versions, so has to be a if / else)
        if hasattr(ensemble, 'sample'):
            sample_function = ensemble.sample
        else:
            sample_function = nengo.dists.get_samples

        # Get maximum rates and intercepts
        max_rates = sample_function(
            nengo_ensemble.max_rates, nengo_ensemble.n_neurons,
            rng=random_number_generator)
        intercepts = sample_function(
            nengo_ensemble.intercepts, nengo_ensemble.n_neurons,
            rng=random_number_generator)

        # Build the neurons
        if nengo_ensemble.gain is None and nengo_ensemble.bias is None:
            gain, bias = nengo_ensemble.neuron_type.gain_bias(
                max_rates, intercepts)
        elif (nengo_ensemble.gain is not None and
                nengo_ensemble.bias is not None):
            gain = sample_function(
                nengo_ensemble.gain, nengo_ensemble.n_neurons,
                rng=random_number_generator)
            bias = sample_function(
                nengo_ensemble.bias, nengo_ensemble.n_neurons,
                rng=random_number_generator)
        else:
            raise NotImplementedError(
                "gain or bias set for {!s}, but not both. Solving for one "
                "given the other is not yet implemented.".format(
                    nengo_ensemble))

        # Scale the encoders
        scaled_encoders = \
            encoders * (gain / nengo_ensemble.radius)[:, numpy.newaxis]

        return {
            "eval_points": eval_points,
            "encoders": encoders,
            "scaled_encoders": scaled_encoders,
            "max_rates": max_rates,
            "intercepts": intercepts,
            "gain": gain,
            "bias": bias}

    @overrides(AbstractNengoApplicationVertex.create_machine_vertices)
    def create_machine_vertices(self):
        pass
