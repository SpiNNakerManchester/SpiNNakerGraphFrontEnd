# Copyright (c) 2020 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from enum import IntEnum

from pacman.model.graphs import AbstractSupportsSDRAMEdges
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
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
    """
    A MachineVertex that stores its own resources.
    """

    SDRAM_PARTITION_BASE_DSG_SIZE = 2 * BYTES_PER_WORD
    SDRAM_PARTITION_COUNTERS = 1 * BYTES_PER_WORD

    def __init__(self, label=None,
                 app_vertex=None, vertex_slice=None, sdram_cost=None):
        super().__init__(
            label=label, app_vertex=app_vertex, vertex_slice=vertex_slice)
        self.__sdram_cost = sdram_cost
        self.__incoming_sdram_partitions = list()
        self.__outgoing_sdram_partitions = list()

    def add_incoming_sdram_partition(self, partition):
        self.__incoming_sdram_partitions.append(partition)

    def add_outgoing_sdram_partition(self, partition):
        self.__outgoing_sdram_partitions.append(partition)

    @property


    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        if (len(self.__incoming_sdram_partitions) +
                len(self.__outgoing_sdram_partitions) == 0):
            raise ValueError("Isolated SDRAM vertex!")
        # Account for only the outgoing requirements here; other end will
        # account for incoming
        outgoing_sdram_requirements = sum(
            part.total_sdram_requirements()
            for part in self.__outgoing_sdram_partitions)
        return ConstantSDRAM(
            SIMULATION_N_BYTES +
            (len(self.__outgoing_sdram_partitions) *
             self.SDRAM_PARTITION_BASE_DSG_SIZE) +
            (len(self.__incoming_sdram_partitions) *
             self.SDRAM_PARTITION_BASE_DSG_SIZE) +
            (self.SDRAM_PARTITION_COUNTERS * 2) + SARK_PER_MALLOC_SDRAM_USAGE +
            outgoing_sdram_requirements)

    @overrides(AbstractSupportsSDRAMEdges.sdram_requirement)
    def sdram_requirement(self, sdram_machine_edge):
        if self.__sdram_cost is None:
            raise NotImplementedError(
                "This vertex has no cost so is not expected to appear "
                "as the pre-vertex to an SDRAM edge!")
        return self.__sdram_cost

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sdram.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        # reserve memory regions
        spec.reserve_memory_region(
            region=DataRegions.SYSTEM, size=SIMULATION_N_BYTES,
            label='systemInfo')

        # simulation .c requirements
        spec.switch_write_focus(DataRegions.SYSTEM)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name()))

        # get counters
        n_out_sdrams = len(self.__outgoing_sdram_partitions)
        n_in_sdrams = len(self.__incoming_sdram_partitions)

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
        for outgoing_partition in self.__outgoing_sdram_partitions:
            spec.write_value(
                outgoing_partition.get_sdram_base_address_for(self))
            spec.write_value(
                outgoing_partition.get_sdram_size_of_region_for(self))

        # add ins
        spec.switch_write_focus(DataRegions.SDRAM_IN)
        spec.write_value(n_in_sdrams)
        for incoming_partition in self.__incoming_sdram_partitions:
            spec.write_value(
                incoming_partition.get_sdram_base_address_for(self))
            spec.write_value(
                incoming_partition.get_sdram_size_of_region_for(self))
        spec.end_specification()
