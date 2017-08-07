import os

import spinnaker_graph_front_end as s
from spinn_front_end_common.utilities.utility_objs import ExecutableStartType
from .test_run_vertex import TestRunVertex
from .test_normal_vertex import TestNormalVertex

# Currently broken!
if __name__ == '__main__':
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(TestRunVertex(
        "test_run_too_long.aplx", ExecutableStartType.SYNC))
    s.add_machine_vertex_instance(TestNormalVertex(10000))
    s.run(1000)
    s.stop()
