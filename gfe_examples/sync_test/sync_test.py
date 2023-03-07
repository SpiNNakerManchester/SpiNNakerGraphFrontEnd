# Copyright (c) 2017 The University of Manchester
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

import os
import spinnaker_graph_front_end as front_end
from gfe_examples.sync_test.sync_test_vertex import (
    SyncTestVertex, SEND_PARTITION)
from pacman.model.graphs.application import ApplicationEdge

front_end.setup(
    n_boards_required=3, model_binary_folder=os.path.dirname(__file__),
    machine_time_step=500000, time_scale_factor=1)

machine = front_end.machine()
boot_chip = machine.boot_chip
boot_vertex = SyncTestVertex(True, f"Lead-{boot_chip.x},{boot_chip.y}")
boot_vertex.set_fixed_location(boot_chip.x, boot_chip.y)
front_end.add_vertex_instance(boot_vertex)
front_end.add_edge_instance(
    ApplicationEdge(boot_vertex, boot_vertex), SEND_PARTITION)

for chip in machine.ethernet_connected_chips:
    if chip != boot_chip:
        sync_vertex = SyncTestVertex(False, f"{chip.x},{chip.y}")
        sync_vertex.set_fixed_location(chip.x, chip.y)
        front_end.add_vertex_instance(sync_vertex)
        front_end.add_edge_instance(
            ApplicationEdge(boot_vertex, sync_vertex), SEND_PARTITION)

front_end.run(10000)

front_end.stop()
