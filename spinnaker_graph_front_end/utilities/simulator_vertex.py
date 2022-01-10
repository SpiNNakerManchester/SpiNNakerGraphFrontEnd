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
import sys
from spinn_utilities.overrides import overrides
from spinn_utilities.log import FormatAdapter
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
log = FormatAdapter(logging.getLogger(__file__))


class SimulatorVertex(MachineVertex, AbstractHasAssociatedBinary):
    """ A machine vertex that is implemented by a binary APLX that supports\
        the spin1_api simulation control protocol.
    """

    __slots__ = ["_binary_name", "__front_end"]

    def __init__(self, label, binary_name, constraints=()):
        """
        :param str label:
            The label for the vertex.
        :param str binary_name:
            The name of the APLX implementing the vertex.
        :param constraints:
            Any placement or key-allocation constraints on the vertex.
        :type constraints:
            ~collections.abc.Iterable(~pacman.model.constraints.AbstractConstraint)
        """
        super().__init__(label, constraints)
        self._binary_name = binary_name
        if not binary_name.lower().endswith(".aplx"):
            log.warning("APLX protocol used but name not matching; "
                        "is {} misnamed?", binary_name)
        # Magic import
        self.__front_end = sys.modules["spinnaker_graph_front_end"]

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return self._binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @property
    def front_end(self):
        """
        The main front end that is handling this simulator vertex.

        :rtype: ~typing.ModuleType
        """
        return self.__front_end

    @property
    def placement(self):
        """
        Get the placement of this vertex.

        .. note::
            Only valid *after* the simulation has run!

        :rtype: ~pacman.model.placements.Placement
        """
        return FecDataView.get_placement_of_vertex(self)

    def get_recording_channel_data(self, recording_id):
        """
        Get the data from a recording channel. The simulation must have
        :py:func:`spinnaker_graph_front_end.run` before this will work,
        and the vertex must set up the recording region beforehand.

        :param int recording_id:
            Which recording channel to fetch
        :return: the data, and whether any data was lost
        :rtype: tuple(bytes, bool)
        """
        buffer_manager = self.front_end.buffer_manager()
        return buffer_manager.get_data_by_placement(
            self.placement, recording_id)

    def generate_system_region(self, spec, region_id=0):
        """
        Generate the system region for the data specification. Assumes that
        the vertex uses the system timestep and time scale factor.

        .. note::
            Do not use this with untimed vertices.

        :param ~data_specification.DataSpecificationGenerator spec:
            The data specification being built
        :param int region_id:
            Which region is the system region.
            Defaults to 0 because it is almost always the first one.
        """
        generate_system_data_region(spec, region_id, self)

    def generate_recording_region(self, spec, region_id, channel_sizes):
        """
        Generate the recording region for the data specification.

        :param ~data_specification.DataSpecificationGenerator spec:
            The data specification being built
        :param int region_id:
            Which region is the recording region.
        :param list(int) sizes:
            The sizes of each of the recording channels.
            The length of the list is the number of recording channels.
        """
        spec.reserve_memory_region(
            region=region_id,
            size=recording_utilities.get_recording_header_size(
                len(channel_sizes)),
            label="Recording")
        spec.switch_write_focus(region_id)
        spec.write_array(recording_utilities.get_recording_header_array(
            channel_sizes))
