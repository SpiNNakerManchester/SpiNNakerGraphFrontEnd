import os
import unittest

import spinn_utilities.package_loader as package_loader

# These are scripts so can not be tested this way.
# They are covered in integeration tests
EXCLUSIONS = ["spinnaker_graph_front_end.examples.Conways."
              "no_edges_examples.conways_no_edges",

              "spinnaker_graph_front_end.examples.Conways."
              "one_no_graph_example.conways_no_graph",

              "spinnaker_graph_front_end.examples.Conways."
              "partitioned_example_a_no_vis_no_buffer.conways_partitioned",

              "spinnaker_graph_front_end.examples.Conways."
              "partitioned_example_b_no_vis_buffer.conways_partitioned",

              "spinnaker_graph_front_end.examples.hello_world.hello_world",
              "spinnaker_graph_front_end.examples.template.python_template",

              "spinnaker_graph_front_end.examples.test_fixed_router."
              "hello_world",
              "spinnaker_graph_front_end.examples.test_fixed_router."
              "hello_world_vertex_clone",

              "spinnaker_graph_front_end.examples.speed_test_solo.main_solo",

              "spinnaker_graph_front_end.examples."
              "speed_tracker_with_protocol.main",

              "spinnaker_graph_front_end.examples."
              "speed_tracker.main",

              "spinnaker_graph_front_end.examples."
              "test_fixed_router_transmitter_reciever.hello_world",

              "spinnaker_graph_front_end.examples."
              "test_retransmission_phase_on_multi_cores.main"]


class ImportAllModule(unittest.TestCase):

    def test_import_all(self):
        if os.environ.get('CONTINUOUS_INTEGRATION', None) == 'True':
            package_loader.load_module("spinnaker_graph_front_end",
                                       exclusions=EXCLUSIONS,
                                       remove_pyc_files=False)
        else:
            package_loader.load_module("spinnaker_graph_front_end",
                                       exclusions=EXCLUSIONS,
                                       remove_pyc_files=True)
