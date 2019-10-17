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

import logging
import os
import spinnaker_graph_front_end as front_end
from pacman.model.graphs.common import EdgeTrafficType
from pacman.model.graphs.impl import ConstantSDRAMMachinePartition
from pacman.model.graphs.machine import MachineEdge
from pacman.model.graphs.machine.machine_sdram_edge import SDRAMMachineEdge
from spinn_front_end_common.utilities.globals_variables import get_simulator
from spinnaker_graph_front_end.examples.sdram_edges_example.src_machine_vertex import SrcMachineVertex
from spinnaker_graph_front_end.examples.sdram_edges_example.dest_machine_vertex import DestMachineVertex

logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

src = SrcMachineVertex(label="bacon")
dest = DestMachineVertex(label="ise")
front_end.add_machine_vertex_instance(src)
front_end.add_machine_vertex_instance(dest)

get_simulator().original_machine_graph.add_outgoing_edge_partition(
    ConstantSDRAMMachinePartition(
        identifier="the bacon path", pre_vertex=src,
        label="the sdram partition for the bacon path"))
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src, dest, sdram_size=8, label="the brown bacon road"), "the bacon path")

front_end.run(200)
front_end.stop()
