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
from time import sleep
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities.exceptions import (
    ExecutableFailedToStopException)
from spinn_front_end_common.utilities.database import DatabaseConnection
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex
import pytest


def test_rte_during_run_forever():

    def start():
        sleep(3.0)
        s.stop_run()

    conn = DatabaseConnection(start, local_port=None)
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(RunVertex(
        "test_rte_during_run.aplx",
        ExecutableType.USES_SIMULATION_INTERFACE))
    s.add_socket_address(None, "localhost", conn.local_port)
    s.run(None)
    with pytest.raises(ExecutableFailedToStopException):
        s.stop()
    conn.close()


if __name__ == "__main__":
    test_rte_during_run_forever()
