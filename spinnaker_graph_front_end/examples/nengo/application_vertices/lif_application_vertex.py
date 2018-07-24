import numpy

from nengo.learning_rules import PES as NengoPES

from pacman.executor.injection_decorator import inject_items
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_probeable import AbstractProbeable
from spinnaker_graph_front_end.examples.nengo.connection_parameters.\
    ensemble_transmission_parameters import \
    EnsembleTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.nengo_exceptions import \
    NengoException


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
        "_probeable_variables_supported_elsewhere",
        "_direct_input"]

    def __init__(
            self, label, rng, seed, eval_points, encoders, scaled_encoders,
            max_rates, intercepts, gain, bias, size_in,
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
        self._direct_input = numpy.zeros(size_in)

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
    def direct_input(self):
        return self._direct_input

    @direct_input.setter
    def direct_input(self, new_value):
        self._direct_input = new_value

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

    @inject_items({"operator_graph": "NengoOperatorGraph"})
    @overrides(
        AbstractNengoApplicationVertex.create_machine_vertices,
        additional_arguments="operator_graph")
    def create_machine_vertices(self, resource_tracker, operator_graph):

        # verify no neurons are incoming  (no idea why)
        incoming_partitions = operator_graph. \
            get_outgoing_edge_partitions_ending_at_vertex(self)
        outgoing_partitions = operator_graph.\
            get_outgoing_edge_partitions_starting_at_vertex(self)

        standard_outgoing_partitions = list()
        outgoing_learnt_partitions = list()
        incoming_modulatory_learning_rules = list()

        # filter incoming partitions
        for incoming_partition in incoming_partitions:
            # verify there's no neurons incoming partitions
            if incoming_partition.identifier.source_port == \
                    constants.ENSEMBLE_INPUT_PORT.NEURONS:
                raise Exception("not suppose to have neurons incoming")

            # locate all modulating incoming partitions
            if incoming_partition.identifier.source_port == \
                    constants.ENSEMBLE_INPUT_PORT.LEARNING_RULE:
                incoming_modulatory_learning_rules.append(
                    incoming_partition.identifier.transmission_parameter
                    .learning_rule)

        # filter outgoing partitions
        for outgoing_partition in outgoing_partitions:
            # locate all standard outgoing partitions
            if outgoing_partition.identifier.source_port == \
                    constants.OUTPUT_PORT.STANDARD:
                standard_outgoing_partitions.append(outgoing_partition)

            # locate all learnt partitions
            if outgoing_partition.identifier.source_port == \
                    constants.ENSEMBLE_OUTPUT_PORT.LEARNT:
                outgoing_learnt_partitions.append(outgoing_partition)

        # locate decoders and n keys
        decoders = numpy.array([])
        if len(standard_outgoing_partitions) != 0:
            decoders, _ = self._get_decoders_and_n_keys(
                standard_outgoing_partitions, True)

        # determine learning rules size out

        # convert to cluster sizes
        cluster_size_out = decoders.shape[0]
        cluster_size_in = self._scaled_encoders.shape[1]
        cluster_learnt_size_out = self._determine_cluster_learnt_size_out(
            outgoing_learnt_partitions, incoming_modulatory_learning_rules)





    def _determine_cluster_learnt_size_out(
            self, outgoing_learnt_partitions,
            incoming_modulatory_learning_rules):
        learnt_decoders = numpy.array([])
        for learnt_outgoing_partition in outgoing_learnt_partitions:
            partition_identifier = learnt_outgoing_partition.identifier
            transmission_parameter = partition_identifier.transmission_parameter
            learning_rule_type = \
                transmission_parameter.learning_rule.learning_rule_type

            # verify that the transmission parameter type is as expected
            if not isinstance(transmission_parameter,
                              EnsembleTransmissionParameters):
                raise NengoException(
                    "the ensemble {} expects a EnsembleTransmissionParameters "
                    "for its learning rules. got {} instead".format(
                        self, transmission_parameter))

            # verify that the learning rule is a PES rule
            if not isinstance(learning_rule_type, NengoPES):
                raise NengoException(
                    "The SpiNNaker Nengo Conversion currently only "
                    "supports PES learning rules")

            # verify that there's a modulatory connection to the learning
            #  rule
            if transmission_parameter.learning_rule not in \
                    incoming_modulatory_learning_rules:
                raise NengoException(
                    "Ensemble %s has outgoing connection with PES "
                    "learning, but no corresponding modulatory "
                    "connection" % self.label)

            decoder_start = learnt_decoders.shape[0]

            # Get new decoders and output keys for learnt connection
            rule_decoders, n_keys = self._get_decoders_and_n_keys(
                [learnt_outgoing_partition], False)

            # If there are no existing decodes, hstacking doesn't
            # work so set decoders to new learnt decoder matrix
            if decoder_start == 0:
                learnt_decoders = rule_decoders
            # Otherwise, stack learnt decoders
            # alongside existing matrix
            else:
                learnt_decoders = numpy.vstack(
                    (learnt_decoders, rule_decoders))
        return learnt_decoders.shape[0]

    @staticmethod
    def _get_decoders_and_n_keys(standard_outgoing_partitions, minimise=False):

        decoders = list()
        n_keys = 0
        for standard_outgoing_partition in standard_outgoing_partitions:
            partition_identifier = standard_outgoing_partition.identifier
            if not isinstance(partition_identifier.transmission_parameter,
                              EnsembleTransmissionParameters):
                raise NengoException(
                    "To determine the decoders and keys, the ensamble {} "
                    "assumes it only has ensemble transmission params. this "
                    "was not the case.".format(self))
            decoder = partition_identifier.transmission_parameter.full_decoders
            if not minimise:
                keep = numpy.array([True for _ in range(decoder.shape[0])])
            else:
                # We can reduce the number of packets sent and the memory
                # requirements by removing columns from the decoder matrix which
                # will always result in packets containing zeroes.
                keep = numpy.any(decoder != 0, axis=1)
            decoders.append(decoder[keep, :])
            n_keys += decoder.shape[0]

        # Stack the decoders
        if len(decoders) > 0:
            decoders = numpy.vstack(decoders)
        else:
            decoders = numpy.array([[]])
        return decoders, n_keys
