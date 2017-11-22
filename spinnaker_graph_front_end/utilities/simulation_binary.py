from pacman.model.decorators import overrides

from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType


class SimulationBinary(AbstractHasAssociatedBinary):
    """This is a simple helper class that handles the case where the vertex
    to which it is mixed in only handles a single binary that supports the
    SpiNNaker simulation interface.
    """

    def __init__(self, binary_name):
        self._binary_name = binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return self._binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE
