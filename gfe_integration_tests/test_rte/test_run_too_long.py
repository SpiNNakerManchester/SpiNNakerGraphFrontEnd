import os
import pytest

import spinnaker_graph_front_end as s
from spinn_front_end_common.utilities.utility_objs import ExecutableStartType
from gfe_integration_tests.test_rte.test_run_vertex import TestRunVertex
from spinnman.exceptions import SpinnmanTimeoutException


def test_run_too_long():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(TestRunVertex(
        "test_run_too_long.aplx",
        ExecutableStartType.USES_SIMULATION_INTERFACE))
    with pytest.raises(SpinnmanTimeoutException):
        s.run(1000)
