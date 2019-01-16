import os
import unittest


class TestExtraMonitor(unittest.TestCase):

    def test_extra_monitor(self):
        import spinnaker_graph_front_end.examples.test_extra_monitor \
            as script_dir
        class_file = script_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.test_extra_monitor.main  # NOQA
