# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
from spinn_utilities.overrides import overrides
from spinn_utilities.log import FormatAdapter
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.utilities.utility_objs import ExecutableType
log = FormatAdapter(logging.getLogger(__file__))


class SimulatorVertex(MachineVertex, AbstractHasAssociatedBinary):
    """ A machine vertex that is implemented by a binary APLX that supports\
        the spin1_api simulation control protocol.
    """

    __slots__ = ["_binary_name"]

    def __init__(self, label, binary_name, constraints=()):
        """
        :param str label:
            The label for the vertex.
        :param str binary_name:
            The name of the APLX implementing the vertex.
        :param constraints:
            Any placement or key-allocation constraints on the vertex.
        :type constraints:
            ~collections.abc.Iterable(
            ~pacman.model.constraints.AbstractConstraint)
        """
        super().__init__(label, constraints)
        self._binary_name = binary_name
        if not binary_name.lower().endswith(".aplx"):
            log.warning("APLX protocol used but name not matching; "
                        "is {} misnamed?", binary_name)

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return self._binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE
