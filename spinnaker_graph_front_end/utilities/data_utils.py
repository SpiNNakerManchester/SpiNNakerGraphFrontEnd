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

from spinn_front_end_common.utilities.constants import SIMULATION_N_BYTES
from spinn_front_end_common.interface.simulation.simulation_utilities import (
    get_simulation_header_array)


def generate_system_data_region(spec, region_id, machine_vertex):
    """ Generate a system data region for time-based simulations.

    :param ~data_specification.DataSpecificationGenerator spec:
        The data specification to write to
    :param int region_id:
        The region to write to
    :param ~pacman.model.graphs.machine.MachineVertex machine_vertex:
        The machine vertex to write for
    :param int machine_time_step:
        The time step of the simulation
    :param int time_scale_factor:
        The time scale of the simulation
    """

    from spinn_utilities.config_holder import get_config_int
    machine_time_step = get_config_int("Machine", "machine_time_step")
    time_scale_factor = get_config_int("Machine", "time_scale_factor")
    # reserve memory regions
    spec.reserve_memory_region(
        region=region_id, size=SIMULATION_N_BYTES, label='systemInfo')

    # simulation .c requirements
    spec.switch_write_focus(region_id)
    spec.write_array(get_simulation_header_array(
        machine_vertex.get_binary_file_name(), machine_time_step,
        time_scale_factor))
