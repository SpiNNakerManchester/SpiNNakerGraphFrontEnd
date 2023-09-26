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
from link_test.link_test_send_vertex import LinkTestSendVertex, PARTITION_NAME
from link_test.link_test_receive_vertex import LinkTestReceiveVertex

WRITE_ROUTES = True
SENDS_PER_TS = 256
DROPS_PER_TS = 0


def run(n_boards=None):
    front_end.setup(model_binary_folder=os.path.dirname(__file__),
                    n_boards_required=n_boards)

    machine = front_end.machine()

    run_time = 10000

    # Put link test on all chips
    senders = dict()
    receivers = dict()
    for c_x, c_y in machine.chip_coordinates:
        receivers[c_x, c_y] = LinkTestReceiveVertex(
            c_x, c_y, SENDS_PER_TS, DROPS_PER_TS, run_time, WRITE_ROUTES)
        front_end.add_machine_vertex_instance(receivers[c_x, c_y])
        senders[c_x, c_y] = LinkTestSendVertex(
            c_x, c_y, SENDS_PER_TS, WRITE_ROUTES)

    # Connect links together
    for chip in machine.chips:
        for link in chip.router.links:
            opposite_link = (link.source_link_id + 3) % 6
            target = receivers[link.destination_x, link.destination_y]
            source = senders[chip.x, chip.y]
            target.set_neighbour(opposite_link, source)
            if not WRITE_ROUTES:
                front_end.add_machine_edge_instance(
                    MachineEdge(source, target), PARTITION_NAME)

    front_end.run(run_time)
    front_end.stop()

    # Check the vertices for failure
    for vertex in receivers.values():
        vertex.check_failure()


if __name__ == "__main__":
    n_boards_req = None
    if len(sys.argv) > 1:
        n_boards_req = int(sys.argv[1])
    run(n_boards_req)
