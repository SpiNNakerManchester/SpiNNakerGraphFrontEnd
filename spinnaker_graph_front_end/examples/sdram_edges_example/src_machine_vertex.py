# Copyright (c) 2019-2020 The University of Manchester
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
from pacman.model.graphs.machine import (
    DestinationSegmentedSDRAMMachinePartition,
    ConstantSDRAMMachinePartition, SourceSegmentedSDRAMMachinePartition)
from pacman.model.resources import ResourceContainer, ConstantSDRAM
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinn_front_end_common.utilities.constants import SYSTEM_BYTES_REQUIREMENT
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_system_data_region)


class SrcMachineVertex(SimulatorVertex, MachineDataSpecableVertex):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('THE_BACON_PATH', 4),
               ('THE_SEGMENTED_BACON_PATH', 5),
               ("THE_SOURCE_SEGMENTED_BACON", 6)])

    BYTES_PER_SDRAM_PARTITION = 8
    BYTES_PER_COUNT = 4
    N_SDRAM_REGIONS = 3

    def __init__(self, label=None, constraints=None):
        SimulatorVertex.__init__(self, label, "bacon_src.aplx", constraints)
        MachineDataSpecableVertex.__init__(self)

    @property
    @inject_items({"machine_graph": "MemoryMachineGraph"})
    @overrides(
        SimulatorVertex.resources_required,
        additional_arguments={"machine_graph"})
    def resources_required(self, machine_graph):
        n_sdram_partitions = len(
            machine_graph.get_costed_edge_partitions_starting_at_vertex(self))
        resources = ResourceContainer(
            sdram=ConstantSDRAM(
                SYSTEM_BYTES_REQUIREMENT +
                (self.BYTES_PER_COUNT * self.N_SDRAM_REGIONS) +
                (n_sdram_partitions * self.BYTES_PER_SDRAM_PARTITION)))
        return resources

    def _set_sdram_region_data(
            self, spec, region_id, n_partitions, partition_type, graph):
        spec.switch_write_focus(region_id)
        spec.write_value(n_partitions)
        for partition in (
                graph.get_costed_edge_partitions_starting_at_vertex(self)):
            if isinstance(partition, partition_type):
                spec.write_value(partition.get_sdram_base_address_for(self))
                spec.write_value(partition.get_sdram_size_of_region_for(self))

    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        # Generate the system data region for simulation .c requirements
        generate_system_data_region(
            spec, self.DATA_REGIONS.SYSTEM.value, self, machine_time_step,
            time_scale_factor)

        constant_partitions = 0
        segmented_partitions = 0
        source_segmented_partitions = 0
        for partition in (
                machine_graph.get_costed_edge_partitions_starting_at_vertex(
                    self)):
            if isinstance(
                    partition, DestinationSegmentedSDRAMMachinePartition):
                segmented_partitions += 1
            elif isinstance(partition, ConstantSDRAMMachinePartition):
                constant_partitions += 1
            elif isinstance(partition, SourceSegmentedSDRAMMachinePartition):
                source_segmented_partitions += 1
            else:
                raise Exception("WHAT DID YOU DO CHIMP!")

        spec.reserve_memory_region(
            region=self.DATA_REGIONS.THE_BACON_PATH.value,
            size=((constant_partitions * self.BYTES_PER_SDRAM_PARTITION) +
                  self.BYTES_PER_COUNT),
            label="the bacon path")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.THE_SEGMENTED_BACON_PATH.value,
            size=((segmented_partitions * self.BYTES_PER_SDRAM_PARTITION) +
                  self.BYTES_PER_COUNT),
            label="the seged bacon path")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.THE_SOURCE_SEGMENTED_BACON.value,
            size=(
                (source_segmented_partitions *
                 self.BYTES_PER_SDRAM_PARTITION) + self.BYTES_PER_COUNT),
            label="the source seged bacon path")

        self._set_sdram_region_data(
            spec, self.DATA_REGIONS.THE_BACON_PATH.value, constant_partitions,
            ConstantSDRAMMachinePartition, machine_graph)
        self._set_sdram_region_data(
            spec, self.DATA_REGIONS.THE_SEGMENTED_BACON_PATH.value,
            segmented_partitions, DestinationSegmentedSDRAMMachinePartition,
            machine_graph)
        self._set_sdram_region_data(
            spec, self.DATA_REGIONS.THE_SOURCE_SEGMENTED_BACON.value,
            source_segmented_partitions, SourceSegmentedSDRAMMachinePartition,
            machine_graph)

        spec.end_specification()
