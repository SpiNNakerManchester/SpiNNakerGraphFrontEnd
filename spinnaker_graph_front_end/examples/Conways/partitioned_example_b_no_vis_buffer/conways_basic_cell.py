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

from enum import IntEnum
from spinn_utilities.overrides import overrides
from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, VariableSDRAM
from pacman.utilities.utility_calls import is_single
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement, n_word_struct)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)


# Regions for populations
class DATA_REGIONS(IntEnum):
    SYSTEM = 0
    TRANSMISSIONS = 1
    STATE = 2
    NEIGHBOUR_INITIAL_STATES = 3
    RESULTS = 4


class ConwayBasicCell(
        SimulatorVertex, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):
    """ Cell which represents a cell within the 2d fabric
    """

    PARTITION_ID = "STATE"

    TRANSMISSION_DATA_SIZE = 2 * BYTES_PER_WORD  # has key and key
    STATE_DATA_SIZE = BYTES_PER_WORD  # 1 or 2 based off dead or alive
    # alive states, dead states
    NEIGHBOUR_INITIAL_STATES_SIZE = 2 * BYTES_PER_WORD
    RECORDING_ELEMENT_SIZE = STATE_DATA_SIZE  # A recording of the state

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
        """
        :param ~.DataSpecificationGenerator spec:
        :param ~.MachineGraph machine_graph:
        :param ~.RoutingInfo routing_info:
        """
        # pylint: disable=arguments-differ
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, DATA_REGIONS.SYSTEM,
                                    self, machine_time_step, time_scale_factor)

        # reserve memory regions
        spec.reserve_memory_region(
            region=DATA_REGIONS.TRANSMISSIONS,
            size=self.TRANSMISSION_DATA_SIZE, label="inputs")
        spec.reserve_memory_region(
            region=DATA_REGIONS.STATE,
            size=self.STATE_DATA_SIZE, label="state")
        spec.reserve_memory_region(
            region=DATA_REGIONS.NEIGHBOUR_INITIAL_STATES,
            size=self.NEIGHBOUR_INITIAL_STATES_SIZE, label="neighour_states")
        spec.reserve_memory_region(
            region=DATA_REGIONS.RESULTS,
            size=recording_utilities.get_recording_header_size(1))

        # get recorded buffered regions sorted
        spec.switch_write_focus(DATA_REGIONS.RESULTS)
        spec.write_array(recording_utilities.get_recording_header_array(
            [self.RECORDING_ELEMENT_SIZE * data_n_time_steps]))

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

        spec.switch_write_focus(DATA_REGIONS.TRANSMISSIONS)
        spec.write_value(int(key is not None))
        spec.write_value(0 if key is None else key)

        # write state value
        spec.switch_write_focus(DATA_REGIONS.STATE)
        spec.write_value(int(bool(self._state)))

        # write neighbours data state
        spec.switch_write_focus(DATA_REGIONS.NEIGHBOUR_INITIAL_STATES)
        alive = sum(edge.pre_vertex.state for edge in edges)
        dead = sum(not edge.pre_vertex.state for edge in edges)
        spec.write_value(alive)
        spec.write_value(dead)

        # End-of-Spec:
        spec.end_specification()

    def get_data(self, buffer_manager, placement):
        # for buffering output info is taken form the buffer manager
        # get raw data, convert to list of booleans
        raw_data, data_missing = buffer_manager.get_data_by_placement(
            placement, 0)

        # do check for missing data
        if data_missing:
            print("missing_data from ({}, {}, {}); ".format(
                placement.x, placement.y, placement.p))

        # return the data, converted to list of booleans
        return [
            bool(element) for element in
            n_word_struct(len(raw_data) // BYTES_PER_WORD).unpack(raw_data)]

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        fixed_sdram = (SYSTEM_BYTES_REQUIREMENT + self.TRANSMISSION_DATA_SIZE +
                       self.STATE_DATA_SIZE +
                       self.NEIGHBOUR_INITIAL_STATES_SIZE +
                       recording_utilities.get_recording_header_size(1) +
                       recording_utilities.get_recording_data_constant_size(1))
        per_timestep_sdram = self.RECORDING_ELEMENT_SIZE
        return ResourceContainer(
            sdram=VariableSDRAM(fixed_sdram, per_timestep_sdram))

    @property
    def state(self):
        return self._state

    def __repr__(self):
        return self.label

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [0]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, DATA_REGIONS.RESULTS, txrx)
