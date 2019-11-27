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

from enum import Enum
from __future__ import division
import struct
from spinn_utilities.overrides import overrides
from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, TimeBasedSDRAM
from pacman.utilities.utility_calls import is_single
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)


class ConwayBasicCell(SimulatorVertex, MachineDataSpecableVertex):
    """ Cell which represents a cell within the 2d fabric
    """

    PARTITION_ID = "STATE"

    TRANSMISSION_DATA_SIZE = 2 * BYTES_PER_WORD  # has key and key
    STATE_DATA_SIZE = 1 * BYTES_PER_WORD  # 1 or 2 based off dead or alive
    # alive states, dead states
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * BYTES_PER_WORD
    # The size of the size of the recording(!)
    RECORDING_HEADER_SIZE = BYTES_PER_WORD
    RECORDING_ELEMENT_SIZE = STATE_DATA_SIZE  # A recording of the state

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('STATE', 2),
               ('NEIGHBOUR_INITIAL_STATES', 3),
               ('RESULTS', 4)])

    def __init__(self, label, state):
        super(ConwayBasicCell, self).__init__(label, "conways_cell.aplx")

        # app specific data items
        self._state = bool(state)

    @inject_items({"data_n_time_steps": "DataNTimeSteps"})
    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification,
        additional_arguments={"data_n_time_steps"})
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor,
            data_n_time_steps):
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, self.DATA_REGIONS.SYSTEM.value,
                                    self, machine_time_step, time_scale_factor)

        # reserve memory regions
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_SIZE, label="inputs")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.STATE.value,
            size=self.STATE_DATA_SIZE, label="state")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value,
            size=self.NEIGHBOUR_INITIAL_STATES_SIZE, label="neighour_states")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RESULTS.value,
            size=(self.RECORDING_HEADER_SIZE +
                  (data_n_time_steps * self.RECORDING_ELEMENT_SIZE)),
            label="results")

        # check got right number of keys and edges going into me
        partitions = \
            machine_graph.get_outgoing_edge_partitions_starting_at_vertex(self)
        if not is_single(partitions):
            raise ConfigurationException(
                "Can only handle one type of partition.")

        # check for duplicates
        edges = list(machine_graph.get_edges_ending_at_vertex(self))
        if len(edges) != 8:
            raise ConfigurationException(
                "I've not got the right number of connections. I have {} "
                "instead of 8".format(
                    len(machine_graph.get_edges_ending_at_vertex(self))))

        for edge in edges:
            if edge.pre_vertex == self:
                raise ConfigurationException(
                    "I'm connected to myself, this is deemed an error"
                    " please fix.")

        # write key needed to transmit with
        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)

        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        spec.write_value(0 if key is None else 1)
        spec.write_value(0 if key is None else key)

        # write state value
        spec.switch_write_focus(
            region=self.DATA_REGIONS.STATE.value)
        spec.write_value(int(bool(self._state)))

        # write neighbours data state
        spec.switch_write_focus(
            region=self.DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value)
        alive = 0
        dead = 0
        for edge in edges:
            if edge.pre_vertex.state:
                alive += 1
            else:
                dead += 1

        spec.write_value(alive)
        spec.write_value(dead)

        # End-of-Spec:
        spec.end_specification()

    def get_data(self, transceiver, placement, n_machine_time_steps):
        # Get the data region base address where results are stored for the
        # core
        record_region_base_address = locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RESULTS.value, transceiver)

        # find how many bytes are needed to be read
        number_of_bytes_to_read = \
            struct.unpack("<I", transceiver.read_memory(
                placement.x, placement.y, record_region_base_address,
                self.RECORDING_HEADER_SIZE))[0]

        # read the bytes
        if number_of_bytes_to_read != (
                n_machine_time_steps * self.RECORDING_ELEMENT_SIZE):
            raise ConfigurationException("number of bytes seems wrong")
        raw_data = transceiver.read_memory(
            placement.x, placement.y,
            record_region_base_address + self.RECORDING_HEADER_SIZE,
            number_of_bytes_to_read)

        # convert to booleans
        return [bool(element) for element in struct.unpack(
            "<{}I".format(n_machine_time_steps), raw_data)]

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        fixed_sdram = (SYSTEM_BYTES_REQUIREMENT + self.TRANSMISSION_DATA_SIZE +
                       self.STATE_DATA_SIZE +
                       self.NEIGHBOUR_INITIAL_STATES_SIZE +
                       self.RECORDING_HEADER_SIZE)
        per_simtime_us = (self.RECORDING_ELEMENT_SIZE /
                          globals_variables.get_simulator().machine_time_step)
        return ResourceContainer(
            sdram=TimeBasedSDRAM(fixed_sdram, per_simtime_us))

    @property
    def state(self):
        return self._state

    def __repr__(self):
        return self.label
