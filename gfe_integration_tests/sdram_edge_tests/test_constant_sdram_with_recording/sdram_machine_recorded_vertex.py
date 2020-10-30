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

from pacman.executor.injection_decorator import inject_items
from pacman.model.graphs import (
    AbstractSupportsSDRAMEdges, AbstractSDRAMPartition)
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, VariableSDRAM
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.constants import (
    SIMULATION_N_BYTES, BYTES_PER_WORD, SARK_PER_MALLOC_SDRAM_USAGE)
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_utilities.overrides import overrides


class SDRAMMachineRecordedVertex(
        MachineVertex, AbstractSupportsSDRAMEdges,
        AbstractHasAssociatedBinary, MachineDataSpecableVertex,
        AbstractReceiveBuffersToHost):
    """ A MachineVertex that stores its own resources.
    """

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('SDRAM_IN', 1),
               ('SDRAM_OUT', 2),
               ('RESULTS', 3)])

    SDRAM_PARTITION_BASE_DSG_SIZE = 2 * BYTES_PER_WORD
    SDRAM_PARTITION_COUNTERS = 1 * BYTES_PER_WORD
    RECORDING_ELEMENT_SIZE = 1 * BYTES_PER_WORD

    def __init__(self, label=None, constraints=None,
                 app_vertex=None, vertex_slice=None, sdram_cost=0):
        super(SDRAMMachineRecordedVertex, self).__init__(
            label=label, constraints=constraints, app_vertex=app_vertex,
            vertex_slice=vertex_slice)
        self._sdram_cost = sdram_cost

    @property
    @inject_items({"app_graph": "MemoryApplicationGraph"})
    @overrides(MachineVertex.resources_required,
               additional_arguments=["app_graph"])
    def resources_required(self, app_graph):
        out_edges = app_graph.get_edges_starting_at_vertex(self.app_vertex)
        in_edges = app_graph.get_edges_starting_at_vertex(self.app_vertex)
        return ResourceContainer(sdram=VariableSDRAM(
            fixed_sdram=(
                SIMULATION_N_BYTES + (
                    len(out_edges) * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
                (len(in_edges) * self.SDRAM_PARTITION_BASE_DSG_SIZE) +
                (self.SDRAM_PARTITION_COUNTERS * 2) +
                SARK_PER_MALLOC_SDRAM_USAGE +
                recording_utilities.get_recording_header_size(1) +
                recording_utilities.get_recording_data_constant_size(1)),
            per_timestep_sdram=self.RECORDING_ELEMENT_SIZE))

    @overrides(AbstractSupportsSDRAMEdges.sdram_requirement)
    def sdram_requirement(self, sdram_machine_edge):
        return self._sdram_cost

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sdram.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @inject_items({"data_n_time_steps": "DataNTimeSteps"})
    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification,
        additional_arguments={"data_n_time_steps"})
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor,
            data_n_time_steps):

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

        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RESULTS.value,
            size=recording_utilities.get_recording_header_size(1))

        # get recorded buffered regions sorted
        spec.switch_write_focus(self.DATA_REGIONS.RESULTS.value)
        spec.write_array(recording_utilities.get_recording_header_array(
            [self.RECORDING_ELEMENT_SIZE * data_n_time_steps]))

        spec.end_specification()

    def get_recorded_region_ids(self):
        return [0]

    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RESULTS.value, txrx)
