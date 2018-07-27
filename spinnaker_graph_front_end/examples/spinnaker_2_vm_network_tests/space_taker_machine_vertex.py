from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import \
    ResourceContainer, CPUCyclesPerTickResource, DTCMResource, SDRAMResource
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.utilities.utility_objs import ExecutableType


class SpaceTakerMachineVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    def __init__(self, x, y):
        MachineVertex.__init__(self, constraints=[
            ChipAndCoreConstraint(x=x, y=y)])
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        self._x = x
        self._y = y

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    def generate_machine_data_specification(self, spec, placement,
                                            machine_graph, routing_info, iptags,
                                            reverse_iptags, machine_time_step,
                                            time_scale_factor):
        spec.end_specification()

    def get_binary_file_name(self):
        return "not_existent.aplx"

    @property
    def resources_required(self):
        resources = ResourceContainer(
            cpu_cycles=CPUCyclesPerTickResource(45),
            dtcm=DTCMResource(100), sdram=SDRAMResource(100))
        return resources
