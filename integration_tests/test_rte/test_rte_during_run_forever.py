import spinnaker_graph_front_end as s
from integration_tests.test_rte.test_run_vertex import TestRunVertex
import os
from time import sleep

s.setup(model_binary_folder=os.path.dirname(__file__))
s.add_machine_vertex_instance(TestRunVertex("test_rte_during_run.aplx"))
s.run(None)
sleep(2.0)
s.stop()
