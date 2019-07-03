import os
import unittest
from spinn_front_end_common.utilities import globals_variables


class TestHelloWorld(unittest.TestCase):

    def setUp(self):
        globals_variables.unset_simulator()

    def test_hello_world(self):
        import spinnaker_graph_front_end.examples.hello_world as hw_dir
        class_file = hw_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.hello_world.hello_world   # NOQA
