# Copyright (c) 2020-2021 The University of Manchester
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

from pacman.model.graphs import AbstractSupportsSDRAMEdges, \
    AbstractSDRAMPartition
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.constants import SIMULATION_N_BYTES, \
    BYTES_PER_WORD
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_utilities.overrides import overrides


class SDRAMMachineVertex(
        MachineVertex, AbstractSupportsSDRAMEdges,
        AbstractHasAssociatedBinary, MachineDataSpecableVertex):
    """ A MachineVertex that stores its own resources.
    """

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('SDRAM_IN', 1),
               ('SDRAM_OUT', 2)])

    SDRAM_PARTITION_BASE_DSG_SIZE = 2 * BYTES_PER_WORD
    SDRAM_PARTITION_COUNTERS = 1 * BYTES_PER_WORD

    def __init__(self, resources, label=None, constraints=None,
                 app_vertex=None, vertex_slice=None, sdram_cost=0):
        super(SDRAMMachineVertex, self).__init__(
            label=label, constraints=constraints, app_vertex=app_vertex,
            vertex_slice=vertex_slice)
        self._resources = resources
        self._sdram_cost = sdram_cost

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        return self._resources

    @overrides(AbstractSupportsSDRAMEdges.sdram_requirement)
    def sdram_requirement(self, sdram_machine_edge):
        return self._sdram_cost

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sdram_const.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        # reserve memory regions
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=SIMULATION_N_BYTES,
            label='systemInfo')

        # simulation .c requirements
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # get counters
        outgoing_partitions = (
            machine_graph.get_outgoing_edge_partitions_starting_at_vertex(
                self))
        n_out_sdrams = 0
        for outgoing_partition in outgoing_partitions:
            if isinstance(outgoing_partition, AbstractSDRAMPartition):
                n_out_sdrams += 1

        incoming_edges = machine_graph.get_edges_ending_at_vertex(self)
        incoming_partitions = list()
        n_in_sdrams = 0
        for incoming_edge in incoming_edges:
            incoming_partition = machine_graph.get_outgoing_partition_for_edge(
                incoming_edge)
            if isinstance(incoming_partition, AbstractSDRAMPartition):
                n_in_sdrams += 1
                incoming_partitions.append(incoming_partition)

        # reserve memory regions
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SDRAM_OUT.value,
            size=(
                (n_out_sdrams * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
                self.SDRAM_PARTITION_COUNTERS), label="sdrams_out")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SDRAM_IN.value,
            size=(
                (n_in_sdrams * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
                self.SDRAM_PARTITION_COUNTERS), label="sdrams_in")

        # add outs
        spec.switch_write_focus(self.DATA_REGIONS.SDRAM_OUT.value)
        spec.write_value(n_out_sdrams)
        for outgoing_partition in outgoing_partitions:
            if isinstance(outgoing_partition, AbstractSDRAMPartition):
                spec.write_value(
                    outgoing_partition.get_sdram_base_address_for(self))
                spec.write_value(
                    outgoing_partition.get_sdram_size_of_region_for(self))

        # add ins
        spec.switch_write_focus(self.DATA_REGIONS.SDRAM_IN.value)
        spec.write_value(n_in_sdrams)
        for incoming_partition in incoming_partitions:
            if isinstance(incoming_partition, AbstractSDRAMPartition):
                spec.write_value(
                    incoming_partition.get_sdram_base_address_for(self))
                spec.write_value(
                    incoming_partition.get_sdram_size_of_region_for(self))
        spec.end_specification()
