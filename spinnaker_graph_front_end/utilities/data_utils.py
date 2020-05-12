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
from spinn_front_end_common.interface.simulation import simulation_utilities


def generate_system_data_region(
        spec, region_id, machine_vertex, machine_time_step, time_scale_factor):
    """ Generate a system data region for time-based simulations

    :param spec: The data specification to write to
    :param region_id: The region to write to
    :param machine_vertex: The machine vertex to write for
    :param machine_time_step: The time step of the simulation
    :param time_scale_factor: The time scale of the simulation
    """

    # reserve memory regions
    spec.reserve_memory_region(
        region=region_id, size=SIMULATION_N_BYTES, label='systemInfo')

    # simulation .c requirements
    spec.switch_write_focus(region_id)
    spec.write_array(simulation_utilities.get_simulation_header_array(
        machine_vertex.get_binary_file_name(), machine_time_step,
        time_scale_factor))


def generate_steps_system_data_region(spec, region_id, machine_vertex):
    """ Generate a system data region for step-based simulations

    :param spec: The data specification to write to
    :param region_id: The region to write to
    :param machine_vertex: The machine vertex to write for
    """
    generate_system_data_region(
        spec, region_id, machine_vertex, machine_time_step=0,
        time_scale_factor=0)
