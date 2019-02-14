import os
from time import sleep
import pytest
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities.exceptions import (
    ExecutableFailedToStopException)
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.test_run_vertex import TestRunVertex


def test_rte_during_run_forever():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(TestRunVertex(
        "test_rte_during_run.aplx",
        ExecutableType.USES_SIMULATION_INTERFACE))
    s.run(None)
    sleep(2.0)
    with pytest.raises(ExecutableFailedToStopException):
        s.stop()
