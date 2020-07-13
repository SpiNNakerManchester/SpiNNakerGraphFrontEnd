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

"""
Hello World program on SpiNNaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""

import logging
import os
import spinnaker_graph_front_end as front_end
from pacman.model.graphs.machine import MachineEdge
from spinnaker_graph_front_end.examples.compressor_test.hello_world_vertex_basic import \
    HelloWorldVertexBasic
from spinnaker_graph_front_end.examples.compressor_test.\
    hello_world_vertex_with_key_allocation import \
    HelloWorldVertexWithKeyAllocation

logger = logging.getLogger(__name__)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

verts = list()
base_keys = [0, 2, 4, 6]
n_keys = [2, 2, 2, 2]
for x in range(4):
    vertex = HelloWorldVertexWithKeyAllocation(
        n_hellos=10, label="Hello World at {}".format(x),
        key=base_keys[x], n_keys=n_keys[x])
    verts.append(vertex)
    front_end.add_machine_vertex_instance(vertex)

idle_verts = list()
for x in range(2):
    vertex = HelloWorldVertexBasic(
        n_hellos=10, label="idle Hello World at {}".format(x))
    idle_verts.append(vertex)
    front_end.add_machine_vertex_instance(vertex)

# add edges
front_end.add_machine_edge_instance(
    MachineEdge(verts[0], idle_verts[0]), "bacon")
front_end.add_machine_edge_instance(
    MachineEdge(verts[1], idle_verts[1]), "bacon")
front_end.add_machine_edge_instance(
    MachineEdge(verts[2], idle_verts[0]), "bacon")
front_end.add_machine_edge_instance(
    MachineEdge(verts[3], idle_verts[1]), "bacon")

front_end.run(10)
front_end.stop()
