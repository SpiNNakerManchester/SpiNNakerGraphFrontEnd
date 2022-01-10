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
from enum import IntEnum

from pacman.model.graphs import AbstractSupportsSDRAMEdges
from pacman.model.graphs.machine import (AbstractSDRAMPartition, MachineVertex)
from pacman.model.resources import ResourceContainer, ConstantSDRAM
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.constants import (
    SIMULATION_N_BYTES, BYTES_PER_WORD, SARK_PER_MALLOC_SDRAM_USAGE)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_utilities.overrides import overrides


class DataRegions(IntEnum):
    SYSTEM = 0
    SDRAM_IN = 1
    SDRAM_OUT = 2


class SDRAMMachineVertex(
        MachineVertex, AbstractSupportsSDRAMEdges,
        AbstractHasAssociatedBinary, MachineDataSpecableVertex):
    """ A MachineVertex that stores its own resources.
    """

    SDRAM_PARTITION_BASE_DSG_SIZE = 2 * BYTES_PER_WORD
    SDRAM_PARTITION_COUNTERS = 1 * BYTES_PER_WORD

    def __init__(self, label=None, constraints=None,
                 app_vertex=None, vertex_slice=None, sdram_cost=0):
        super().__init__(
            label=label, constraints=constraints, app_vertex=app_vertex,
            vertex_slice=vertex_slice)
        self._sdram_cost = sdram_cost

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        app_graph = FecDataView.get_runtime_graph()
        out_edges = app_graph.get_edges_starting_at_vertex(self.app_vertex)
        in_edges = app_graph.get_edges_starting_at_vertex(self.app_vertex)
        return ResourceContainer(sdram=ConstantSDRAM(
            SIMULATION_N_BYTES + (
                len(out_edges) * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
            (len(in_edges) * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
            (self.SDRAM_PARTITION_COUNTERS * 2) + SARK_PER_MALLOC_SDRAM_USAGE))

    @overrides(AbstractSupportsSDRAMEdges.sdram_requirement)
    def sdram_requirement(self, sdram_machine_edge):
        return self._sdram_cost

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sdram.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags):

        # reserve memory regions
        spec.reserve_memory_region(
            region=DataRegions.SYSTEM, size=SIMULATION_N_BYTES,
            label='systemInfo')

        # simulation .c requirements
        spec.switch_write_focus(DataRegions.SYSTEM)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name()))

        # get counters
        outgoing_partitions = list(
            machine_graph.get_sdram_edge_partitions_starting_at_vertex(
                self))
        n_out_sdrams = len(outgoing_partitions)

        incoming_partitions = list(
            machine_graph.get_sdram_edge_partitions_ending_at_vertex(self))
        n_in_sdrams = len(incoming_partitions)

        # reserve memory regions
        spec.reserve_memory_region(
            region=DataRegions.SDRAM_OUT,
            size=(
                (n_out_sdrams * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
                self.SDRAM_PARTITION_COUNTERS), label="sdrams_out")
        spec.reserve_memory_region(
            region=DataRegions.SDRAM_IN,
            size=(
                (n_in_sdrams * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
                self.SDRAM_PARTITION_COUNTERS), label="sdrams_in")

        # add outs
        spec.switch_write_focus(DataRegions.SDRAM_OUT)
        spec.write_value(n_out_sdrams)
        for outgoing_partition in outgoing_partitions:
            spec.write_value(
                outgoing_partition.get_sdram_base_address_for(self))
            spec.write_value(
                outgoing_partition.get_sdram_size_of_region_for(self))

        # add ins
        spec.switch_write_focus(DataRegions.SDRAM_IN)
        spec.write_value(n_in_sdrams)
        for incoming_partition in incoming_partitions:
            if isinstance(incoming_partition, AbstractSDRAMPartition):
                spec.write_value(
                    incoming_partition.get_sdram_base_address_for(self))
                spec.write_value(
                    incoming_partition.get_sdram_size_of_region_for(self))
        spec.end_specification()
