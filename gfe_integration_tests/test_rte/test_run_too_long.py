import os
import pytest
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import globals_variables
from spinnman.exceptions import SpinnmanTimeoutException
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex


def test_run_too_long():
    globals_variables.unset_simulator()
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(RunVertex(
        "test_run_too_long.aplx",
        ExecutableType.USES_SIMULATION_INTERFACE))
    with pytest.raises(SpinnmanTimeoutException):
        s.run(1000)
