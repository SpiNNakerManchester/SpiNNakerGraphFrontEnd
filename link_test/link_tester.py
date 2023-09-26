# Copyright (c) 2023 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
from pacman.model.graphs.machine.machine_edge import MachineEdge
import spinnaker_graph_front_end as front_end
from link_test.link_test_vertex import LinkTestVertex, PARTITION_NAME


def run(n_chips=None):
    front_end.setup(model_binary_folder=os.path.dirname(__file__),
                    n_chips_required=n_chips)

    machine = front_end.machine()

    run_time = 10000

    # Put link test on all chips
    chips = dict()
    for c_x, c_y in machine.chip_coordinates:
        chips[c_x, c_y] = LinkTestVertex(c_x, c_y, 256, 0, run_time)
        front_end.add_machine_vertex_instance(chips[c_x, c_y])

    # Connect links together
    for chip in machine.chips:
        for link in chip.router.links:
            opposite_link = (link.source_link_id + 3) % 6
            target = chips[link.destination_x, link.destination_y]
            source = chips[chip.x, chip.y]
            target.set_neighbour(opposite_link, source)
            front_end.add_machine_edge_instance(
                MachineEdge(source, target), PARTITION_NAME)

    front_end.run(run_time)
    front_end.stop()

    # Check the vertices for failure
    for vertex in chips.values():
        vertex.check_failure()


if __name__ == "__main__":
    n_chips = None
    if len(sys.argv) > 0:
        n_chips = int(sys.argv[0])
    run(n_chips)
