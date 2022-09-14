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

import os
import spinnaker_graph_front_end as front_end
from gfe_examples.sync_test.sync_test_vertex import (
    SyncTestVertex, SEND_PARTITION)
from pacman.model.graphs.common import ChipAndCore
from pacman.model.graphs.application import ApplicationEdge

front_end.setup(
    n_boards_required=3, model_binary_folder=os.path.dirname(__file__),
    machine_time_step=500000, time_scale_factor=1)

machine = front_end.machine()
boot_chip = machine.boot_chip
boot_vertex = SyncTestVertex(True, f"Lead-{boot_chip.x},{boot_chip.y}")
boot_vertex.set_fixed_location(ChipAndCore(boot_chip.x, boot_chip.y))
front_end.add_vertex_instance(boot_vertex)
front_end.add_edge_instance(
    ApplicationEdge(boot_vertex, boot_vertex), SEND_PARTITION)

for chip in machine.ethernet_connected_chips:
    if chip != boot_chip:
        sync_vertex = SyncTestVertex(False, f"{chip.x},{chip.y}")
        sync_vertex.set_fixed_location(ChipAndCore(chip.x, chip.y))
        front_end.add_vertex_instance(sync_vertex)
        front_end.add_edge_instance(
            ApplicationEdge(boot_vertex, sync_vertex), SEND_PARTITION)

front_end.run(10000)

front_end.stop()
