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
from spinn_utilities.log import FormatAdapter
import spinnaker_graph_front_end as front_end
from gfe_examples.hello_world.hello_world_vertex import HelloWorldVertex

logger = FormatAdapter(logging.getLogger(__name__))

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))

# Put HelloWorldVertex onto 16 cores
total_number_of_cores = 16
for x in range(total_number_of_cores):
    front_end.add_machine_vertex_instance(
        HelloWorldVertex(n_hellos=10, label=f"Hello World at {x}"))

front_end.run(10)
front_end.run(10)

if not front_end.use_virtual_machine():
    for placement in sorted(front_end.placements().placements,
                            key=lambda p: (p.x, p.y, p.p)):
        if isinstance(placement.vertex, HelloWorldVertex):
            hello_world = placement.vertex.read()
            logger.info("{}, {}, {} > {}",
                placement.x, placement.y, placement.p, hello_world)

front_end.stop()
