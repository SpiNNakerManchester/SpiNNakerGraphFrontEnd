from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType


class SimulatorVertex(
        MachineVertex, AbstractHasAssociatedBinary):
    """ A machine vertex that is implemented by a binary APLX that supports\
        the spin1_api simulation control protocol.
    """

    __slots__ = ["_binary_name"]

    def __init__(self, label, binary_name, constraints=None):
        super(SimulatorVertex, self).__init__(label, constraints)
        self._binary_name = binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return self._binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE
