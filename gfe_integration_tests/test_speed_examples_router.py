import os
import unittest


class TestSpeedRouter(unittest.TestCase):

    def test_Solo(self):
        import spinnaker_graph_front_end.examples.speed_test_solo as \
            script_dir
        class_file = script_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print path
        os.chdir(path)
        import spinnaker_graph_front_end.examples.speed_test_solo.main_solo    # NOQA

    def test_tracker(self):
        import spinnaker_graph_front_end.examples.speed_tracker as script_dir
        class_file = script_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print path
        os.chdir(path)
        import spinnaker_graph_front_end.examples.speed_tracker.main  # NOQA

    def test_with_protocol(self):
        import spinnaker_graph_front_end.examples.speed_tracker_with_protocol \
            as script_dir
        class_file = script_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print path
        os.chdir(path)
        import spinnaker_graph_front_end.examples.speed_tracker_with_protocol.main  # NOQA
