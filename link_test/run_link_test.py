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

from time import sleep
import os
import tempfile
import sys
import traceback
import pytest
from pacman.model.graphs.machine.machine_edge import MachineEdge
from spalloc.job import Job
from spalloc.states import JobState
import spinnaker_graph_front_end as front_end
from link_test.link_test_vertex import LinkTestVertex, PARTITION_NAME
from _pytest.outcomes import Skipped


class LinkTest(object):

    def do_run(self):
        front_end.setup(model_binary_folder=os.path.dirname(__file__))

        machine = front_end.machine()

        run_time = 10000

        # Put link test on all chips
        chips = dict()
        for c_x, c_y in machine.chip_coordinates:
            chips[c_x, c_y] = LinkTestVertex(c_x, c_y, 100, 1, run_time)
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


boards = [(x, y, b) for x in range(20) for y in range(20) for b in range(3)]


@pytest.mark.parametrize("b_x,b_y,b_b", boards)
def test_run(b_x, b_y, b_b):
    tmp_dir = os.path.abspath(os.path.join(
        front_end.__path__[0], os.path.pardir, "link_test"))
    job = Job(b_x, b_y, b_b, hostname="spinnaker.cs.man.ac.uk",
              owner="Jenkins Link Test")
    # Sleep before checking for queued in case of multiple jobs running
    sleep(2.0)
    if job.state == JobState.queued:
        job.destroy("Queued")
        pytest.skip(f"Board {b_x}, {b_y}, {b_b} is in use")
    elif job.state == JobState.destroyed:
        pytest.skip(f"Board {b_x}, {b_y}, {b_b} could not be allocated")
    with job:
        with tempfile.TemporaryDirectory(
                prefix=f"{b_x}_{b_y}_{b_b}", dir=tmp_dir) as tmpdir:
            os.chdir(tmpdir)
            with open("spiNNakerGraphFrontEnd.cfg", "w", encoding="utf-8") as f:
                f.write("[Machine]\n")
                f.write("spalloc_server = None\n")
                f.write(f"machine_name = {job.hostname}\n")
                f.write("version = 5\n")
            test = LinkTest()
            test.do_run()


if __name__ == "__main__":
    for x, y, b in boards:
        print("", file=sys.stderr,)
        print(f"*************** Testing {x}, {y}, {b} *******************",
              file=sys.stderr)
        try:
            test_run(x, y, b)
        except Skipped:
            traceback.print_exc()
