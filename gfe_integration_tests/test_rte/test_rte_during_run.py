import os
import pytest

import spinnaker_graph_front_end as s
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from gfe_integration_tests.test_rte.test_run_vertex import TestRunVertex
from spinnman.exceptions import SpinnmanException
import traceback


def test_rte_during_run():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(TestRunVertex(
        "test_rte_during_run.aplx",
        ExecutableType.USES_SIMULATION_INTERFACE))
    with pytest.raises(SpinnmanException):
        try:
            s.run(1000)
        except Exception:
            traceback.print_exc()
            raise
