import os
import unittest
from spinn_front_end_common.utilities import globals_variables


class TestConwayExamples(unittest.TestCase):

    def setUp(self):
        globals_variables.unset_simulator()

    def test_one_no_graph(self):
        import spinnaker_graph_front_end.examples.Conways.no_edges_examples.conways_basic_cell  # NOQA

    def test_conways_no_edges(self):
        import spinnaker_graph_front_end.examples.Conways.\
            one_no_graph_example as conways_ng
        class_file = conways_ng.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.Conways.one_no_graph_example.conways_no_graph  # NOQA

    def test_conways_partitioned_a(self):
        import spinnaker_graph_front_end.examples.Conways.\
            partitioned_example_a_no_vis_no_buffer as conways_a
        class_file = conways_a.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.Conways.partitioned_example_a_no_vis_no_buffer.conways_partitioned   # NOQA

    def test_conways_partitioned_b(self):
        import spinnaker_graph_front_end.examples.Conways.\
            partitioned_example_b_no_vis_buffer as conways_b
        class_file = conways_b.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        os.chdir(path)
        import spinnaker_graph_front_end.examples.Conways.partitioned_example_b_no_vis_buffer.conways_partitioned  # NOQA
