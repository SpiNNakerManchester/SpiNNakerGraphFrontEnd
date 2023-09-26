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

import time
import os
import tempfile
from shutil import rmtree
import pytest
from spinnman.spalloc.spalloc_client import SpallocClient
from spinnman.spalloc.spalloc_state import SpallocState
from link_test.link_tester import run

SPALLOC_URL = "https://spinnaker.cs.man.ac.uk/spalloc"
SPALLOC_USERNAME = "jenkins"
SPALLOC_PASSWORD = os.getenv("SPALLOC_PASSWORD")
SPALLOC_MACHINE = "SpiNNaker1M"
WIDTH = 2
HEIGHT = 2


class LinkTest(object):

    def do_run(self):
        run()


boards = [(b_x, b_y) for b_x in range(0, 20, 2) for b_y in range(0, 20, 2)]
boards += [(b_x, b_y) for b_x in range(1, 20, 2) for b_y in range(1, 20, 2)]


@pytest.mark.parametrize("x,y", boards)
def test_run(x, y):
    test_dir = os.path.dirname(__file__)
    client = SpallocClient(SPALLOC_URL, SPALLOC_USERNAME, SPALLOC_PASSWORD)
    job = client.create_job_rect_at_board(
        WIDTH, HEIGHT, triad=(x, y, 0), machine_name=SPALLOC_MACHINE)
    with job:
        job.launch_keepalive_task()
        # Wait for not queued for up to 30 seconds
        time.sleep(1.0)
        state = job.get_state(wait_for_change=True)
        # If queued or destroyed skip test
        if state == SpallocState.QUEUED:
            job.destroy("Queued")
            pytest.skip(f"Some boards starting at {x}, {y}, 0 are in use"
                        f" on job {job}")
        elif state == SpallocState.DESTROYED:
            pytest.skip(
                f"Boards {x}, {y}, 0 could not be allocated on job {job}")
        # Actually wait for ready now (as might be powering on)
        job.wait_until_ready()
        tmpdir = tempfile.mkdtemp(prefix=f"{x}_{y}_0", dir=test_dir)
        os.chdir(tmpdir)
        with open("spynnaker.cfg", "w", encoding="utf-8") as f:
            f.write("[Machine]\n")
            f.write("spalloc_server = None\n")
            f.write(f"machine_name = {job.get_root_host()}\n")
            f.write("version = 5\n")
            f.write("\n")
            f.write("[Reports]\n")
            f.write("reports_enabled = False\n")
            f.write("write_routing_table_reports = False\n")
            f.write("write_routing_tables_from_machine_reports = False\n")
            f.write("write_tag_allocation_reports = False\n")
            f.write("write_algorithm_timings = False\n")
            f.write("write_sdram_usage_report_per_chip = False\n")
            f.write("write_partitioner_reports = False\n")
            f.write("write_application_graph_placer_report = False\n")
            f.write("write_redundant_packet_count_report = False\n")
            f.write("write_data_speed_up_reports = False\n")
            f.write("write_router_info_report = False\n")
            f.write("write_network_specification_report = False\n")
            f.write("write_provenance = False\n")
            f.write("read_graph_provenance_data = False\n")
            f.write("read_placements_provenance_data = False\n")
            f.write("read_profile_data = False\n")

        test = LinkTest()
        test.do_run()

        # If no errors we will get here and we can remove the tree;
        # then only error folders will be left
        rmtree(tmpdir)


if __name__ == "__main__":
    link_test = LinkTest()
    link_test.do_run()
