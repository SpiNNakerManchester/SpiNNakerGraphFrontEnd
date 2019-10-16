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
from pacman.model.graphs.common import EdgeTrafficType
from pacman.model.resources import ResourceContainer, ConstantSDRAM
from spinn_front_end_common.abstract_models.impl import MachineDataSpecableVertex
from spinn_front_end_common.utilities.constants import SYSTEM_BYTES_REQUIREMENT
from spinnaker_graph_front_end.examples.sdram_edges_example.src_machine_vertex import SrcMachineVertex
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import generate_system_data_region


class DestMachineVertex(SimulatorVertex, MachineDataSpecableVertex):

    def __init__(self, label=None, constraints=None):
        SimulatorVertex.__init__(self, label, "bacon_dest.aplx", constraints)
        MachineDataSpecableVertex.__init__(self)

    @property
    def resources_required(self):
        resources = ResourceContainer(sdram=ConstantSDRAM(SYSTEM_BYTES_REQUIREMENT + 8))
        return resources

    def generate_machine_data_specification(self, spec, placement, machine_graph, routing_info, iptags, reverse_iptags,
                                            machine_time_step, time_scale_factor):
        # Generate the system data region for simulation .c requirements
        generate_system_data_region(spec, self.DATA_REGIONS.SYSTEM.value, self, machine_time_step, time_scale_factor)
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.THE_BACON_PATH.value, size=8, label="the bacon path")
        spec.switch_write_focus(self.DATA_REGIONS.THE_BACON_PATH.value)

        for edge in machine_graph.get_edges_ending_at_vertex(self):
            if isinstance(edge.pre_vertex, SrcMachineVertex):
                if edge.traffic_type == EdgeTrafficType.SDRAM:
                    sdram_partition = machine_graph.get_outgoing_partition_for_edge(edge)
                    spec.switch_write_focus(self.REGIONS.SDRAM_EDGE.value)
                    spec.write_value(sdram_partition.sdram_base_address)
                    spec.write_value(sdram_partition.total_sdram_requirements())
        spec.end_specification()
