import spinnaker_graph_front_end as s
from integration_tests.test_rte.test_run_vertex import TestRunVertex
import os
from spinn_front_end_common.utilities.utility_objs.executable_start_type \
    import ExecutableStartType

s.setup(model_binary_folder=os.path.dirname(__file__))
s.add_machine_vertex_instance(
    TestRunVertex("test_rte_start.aplx", ExecutableStartType.RUNNING))
s.run(1000)
s.stop()
