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
from pacman.model.graphs.machine import (
    ConstantSDRAMMachinePartition, DestinationSegmentedSDRAMMachinePartition,
    SourceSegmentedSDRAMMachinePartition)
from pacman.model.graphs.machine.machine_sdram_edge import SDRAMMachineEdge
from spinnaker_graph_front_end.examples.sdram_edges_example.\
    src_machine_vertex import SrcMachineVertex
from spinnaker_graph_front_end.examples.sdram_edges_example.\
    dest_machine_vertex import DestMachineVertex

logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

src = SrcMachineVertex(label="bacon")
dest = DestMachineVertex(label="ise")
front_end.add_machine_vertex_instance(src)
front_end.add_machine_vertex_instance(dest)

src2 = SrcMachineVertex(label="bacon2")
dest2 = DestMachineVertex(label="ise2")
front_end.add_machine_vertex_instance(src2)
front_end.add_machine_vertex_instance(dest2)

src3 = SrcMachineVertex(label="bacon3")
dest3 = DestMachineVertex(label="ise3")
front_end.add_machine_vertex_instance(src3)
front_end.add_machine_vertex_instance(dest3)

# const
front_end.add_machine_outgoing_partition_instance(
    ConstantSDRAMMachinePartition(
        identifier="the bacon path", pre_vertex=src,
        label="the sdram partition for the bacon path"))
front_end.add_machine_outgoing_partition_instance(
    ConstantSDRAMMachinePartition(
        identifier="the bacon path2", pre_vertex=src2,
        label="the sdram partition for the bacon path2"))
front_end.add_machine_outgoing_partition_instance(
    ConstantSDRAMMachinePartition(
        identifier="the bacon path3", pre_vertex=src3,
        label="the sdram partition for the bacon path3"))

# dest seg
front_end.add_machine_outgoing_partition_instance(
    DestinationSegmentedSDRAMMachinePartition(
        identifier="the bacon path4", pre_vertex=src3,
        label="the sdram partition for the bacon path4"))

# src seg
front_end.add_machine_outgoing_partition_instance(
    SourceSegmentedSDRAMMachinePartition(
        identifier="the bacon path5", pre_vertices=[src3, src],
        label="the sdram partition for the bacon path5"))

# const from 1 to 1
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src, dest, sdram_size=8, label="the brown bacon road"), "the bacon path")

# const many to one
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src, dest, sdram_size=8, label="the brown bacon road"), "the bacon path2")
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src2, dest, sdram_size=8, label="the brown bacon road"), "the bacon path2")

# const one to many
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src, dest, sdram_size=8, label="the brown bacon road"), "the bacon path3")
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src2, dest, sdram_size=8, label="the brown bacon road"), "the bacon path3")

# segmented 1 to many
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src, dest, sdram_size=24, label="the brown bacon road"), "the bacon path4")
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src2, dest, sdram_size=8, label="the brown bacon road"), "the bacon path4")

# segmented many to 1
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src, dest, sdram_size=24, label="the brown bacon road"), "the bacon path5")
front_end.add_machine_edge_instance(SDRAMMachineEdge(
    src3, dest, sdram_size=8, label="the brown bacon road"), "the bacon path5")

front_end.run(200)
front_end.stop()
