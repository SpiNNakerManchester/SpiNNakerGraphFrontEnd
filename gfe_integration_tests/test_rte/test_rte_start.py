import os

import spinnaker_graph_front_end as s
from spinn_front_end_common.utilities.utility_objs import ExecutableStartType
from .test_run_vertex import TestRunVertex

s.setup(model_binary_folder=os.path.dirname(__file__))
s.add_machine_vertex_instance(
    TestRunVertex("test_rte_start.aplx", ExecutableStartType.RUNNING))
s.run(1000)
s.stop()
