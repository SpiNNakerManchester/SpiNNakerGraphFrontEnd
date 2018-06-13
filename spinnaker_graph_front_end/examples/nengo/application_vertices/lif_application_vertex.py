import numpy

import nengo
from nengo import builder as nengo_builder
from nengo.utils import numpy as nengo_numpy
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex


class LIFApplicationVertex(
        AbstractNengoApplicationVertex):

    __slots__ = [
        "_eval_points",
        "_encoders",
        "_scaled_encoders",
        "_max_rates",
        "_intercepts",
        "_gain",
        "_bias"]

    def __init__(
            self, label, rng, eval_points, encoders, scaled_encoders,
            max_rates, intercepts, gain, bias):
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
        AbstractNengoApplicationVertex.__init__(self, label=label, rng=rng)
        self._eval_points = eval_points
        self._encoders = encoders
        self._scaled_encoders = scaled_encoders
        self._max_rates = max_rates
        self._intercepts = intercepts
        self._gain = gain
        self._bias = bias

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

    @staticmethod
    def generate_parameters_from_ensemble(
            nengo_ensemble, random_number_generator):
        """ goes through the nengo ensemble object and extracts the 
        parameters for the lif neurons
        
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
        if hasattr(nengo_ensemble, 'sample'):
            sample_function = nengo_ensemble.sample
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
