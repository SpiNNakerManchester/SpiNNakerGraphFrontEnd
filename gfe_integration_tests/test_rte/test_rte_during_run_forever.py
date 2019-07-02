import os
from time import sleep
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities.exceptions import (
    ExecutableFailedToStopException)
from spinn_front_end_common.utilities.database import DatabaseConnection
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex
import pytest


conn = None


def start():
    sleep(2.0)
    s.stop_run()


conn = DatabaseConnection(start, local_port=None)


def test_rte_during_run_forever():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(RunVertex(
        "test_rte_during_run.aplx",
        ExecutableType.USES_SIMULATION_INTERFACE))
    s.add_socket_address(None, "localhost", conn.local_port)
    s.run(None)
    conn.close()
    with pytest.raises(ExecutableFailedToStopException):
        s.stop()


if __name__ == "__main__":
    test_rte_during_run_forever()
