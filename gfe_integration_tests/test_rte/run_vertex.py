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

from pacman.model.graphs.machine import SimpleMachineVertex
from pacman.model.resources import ResourceContainer
from spinn_front_end_common.abstract_models import (
    AbstractHasAssociatedBinary, AbstractGeneratesDataSpecification)
from spinn_front_end_common.interface.simulation import (
    simulation_utilities as
    utils)
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.utilities.constants import SIMULATION_N_BYTES


class RunVertex(
        SimpleMachineVertex, AbstractHasAssociatedBinary,
        AbstractGeneratesDataSpecification):

    def __init__(self, aplx_file, executable_type):
        super(RunVertex, self).__init__(ResourceContainer())
        self._aplx_file = aplx_file
        self._executable_type = executable_type

    def get_binary_file_name(self):
        return self._aplx_file

    def get_binary_start_type(self):
        return self._executable_type

    def generate_data_specification(self, spec, placement):
        spec.reserve_memory_region(0, SIMULATION_N_BYTES)
        spec.switch_write_focus(0)
        spec.write_array(utils.get_simulation_header_array(
            self._aplx_file, 1000, time_scale_factor=1))
        spec.end_specification()

    @property
    def timestep_in_us(self):
        return globals_variables.get_simulator().user_timestep_in_us

    def simtime_in_us_to_timesteps(self, simtime_in_us):
        """
        Helper function to convert simtime in us to whole timestep

        This function verfies that the simtime is a multile of the timestep.

        :param simtime_in_us: a simulation time in us
        :type simtime_in_us: int
        :return: the exact number of timeteps covered by this simtime
        :rtype: int
        :raises ValueError: If the simtime is not a mutlple of the timestep
        """
        n_timesteps = simtime_in_us // self.timestep_in_us
        check = n_timesteps * self.timestep_in_us
        if check != simtime_in_us:
            raise ValueError(
                "The requested time {} is not a multiple of the timestep {}"
                "".format(simtime_in_us, self.timestep_in_us))
        return n_timesteps
