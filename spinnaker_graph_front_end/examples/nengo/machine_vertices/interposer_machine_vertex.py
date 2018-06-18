from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from enum import Enum

from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_accepts_multicast_signals import \
    AcceptsMulticastSignals


class InterposerMachineVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        AcceptsMulticastSignals):
    """Portion of the rows of the transform assigned to a parallel filter
    group, represents the load assigned to a single processing core.
    """

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('KEYS', 1),
               ('INPUT_FILTERS', 2),
               ('INPUT_ROUTING', 3),
               ('TRANSFORM', 4)])

    def __init__(self, size_in, max_cols, max_row, label, constraints):
        MachineVertex.__init__(self, label=label, constraints=constraints)
        AbstractHasAssociatedBinary.__init__(self)
        AcceptsMulticastSignals.__init__(self)

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(self, spec, placement,
                                            machine_graph, routing_info,
                                            iptags,
                                            reverse_iptags,
                                            machine_time_step,
                                            time_scale_factor):
        pass

    @overrides(AcceptsMulticastSignals.accepts_multicast_signals)
    def accepts_multicast_signals(self, transmission_params):
        return transmission_params.projects_to(self._column_slice)

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "interposer.aplx"  # this was filter in mundy code

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        pass

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE
