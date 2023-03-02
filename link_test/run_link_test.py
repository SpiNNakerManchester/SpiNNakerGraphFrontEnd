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

from time import sleep
import os
import tempfile
import sys
import traceback
import pytest
from spalloc.job import Job
from spalloc.states import JobState
import spinnaker_graph_front_end as front_end
from _pytest.outcomes import Skipped
from link_test.link_tester import run


class LinkTest(object):

    def do_run(self):
        run()


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
