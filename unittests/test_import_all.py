import os
import unittest

import spinn_utilities.package_loader as package_loader


class ImportAllModule(unittest.TestCase):

    BROKEN = ["spinnaker_graph_front_end.examples.heat_demo.heat_demo",

              "spinnaker_graph_front_end.examples.Conways."
              "1_no_graph_example.conways_no_graph",

              "spinnaker_graph_front_end.examples."
              "Conways.no_edges_examples.conways_no_edges",

              "spinnaker_graph_front_end.examples.Conways."
              "partitioned_example_a_no_vis_no_buffer.conways_partitioned",

              "spinnaker_graph_front_end.examples."
              "Conways.partitioned_example_b_no_vis_buffer."
              "conways_partitioned",

              "spinnaker_graph_front_end.examples."
              "Conways.partitioned_example_c_vis_buffer.conways_partitioned",

              "spinnaker_graph_front_end.examples.hello_world.hello_world"]

    BROKEN = []

    def test_import_all(self):
        print self.BROKEN

        if os.environ.get('CONTINUOUS_INTEGRATION', None) == 'True':
            package_loader.load_module("spinnaker_graph_front_end",
                                       remove_pyc_files=False,
                                       exclusions=self.BROKEN)
        else:
            package_loader.load_module("spinnaker_graph_front_end",
                                       remove_pyc_files=True,
                                       exclusions=self.BROKEN)

