import os
import pytest
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinnman.exceptions import SpinnmanException
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex


def test_rte_at_start():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(
        RunVertex(
            "test_rte_start.aplx",
            ExecutableType.USES_SIMULATION_INTERFACE))
    with pytest.raises(SpinnmanException):
        s.run(1000)
