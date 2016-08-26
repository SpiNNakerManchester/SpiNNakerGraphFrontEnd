from pacman.model.decorators.overrides import overrides

from spynnaker.pyNN.models.neural_properties.neural_parameter \
    import NeuronParameter
from spynnaker.pyNN.models.neuron.synapse_types.abstract_synapse_type \
    import AbstractSynapseType

from data_specification.enums.data_type import DataType


class ConwaysSynapseTypes(AbstractSynapseType):
    """
    filter for atoms for stuff
    """

    def __init__(self, states):
        AbstractSynapseType.__init__(self)
        self._states = list()
        for state in states:
            if state:
                self._states.append(0)
            else:
                self._states.append(1)

    @overrides(AbstractSynapseType.get_n_synapse_types)
    def get_n_synapse_types(self):
        return 1

    @overrides(AbstractSynapseType.get_n_synapse_type_parameters)
    def get_n_synapse_type_parameters(self):
        return 1

    @overrides(AbstractSynapseType.get_synapse_targets)
    def get_synapse_targets(self):
        return "state"

    @overrides(AbstractSynapseType.get_synapse_id_by_target)
    def get_synapse_id_by_target(self, target):
        if target == 0:
            return "state"
        else:
            return None

    @overrides(AbstractSynapseType.get_n_cpu_cycles_per_neuron)
    def get_n_cpu_cycles_per_neuron(self):
        return 0

    @overrides(AbstractSynapseType.get_synapse_type_parameters)
    def get_synapse_type_parameters(self):
        return [NeuronParameter(self._states, DataType.UINT32)]
