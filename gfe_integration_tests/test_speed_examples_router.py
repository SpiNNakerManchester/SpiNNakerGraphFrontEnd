import os
import unittest


class TestSpeedRouter(unittest.TestCase):

    def test_with_timer_setup(self):
        import spinnaker_graph_front_end.examples.test_timer_setup_cost \
            as script_dir
        class_file = script_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.test_timer_setup_cost.test_timer_setup_cost  # NOQA
