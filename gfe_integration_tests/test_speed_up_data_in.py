import os
import unittest


class TestDataSpeedUpExamples(unittest.TestCase):

    def test_multi_boards(self):
        import spinnaker_graph_front_end.examples.\
            test_data_in_speed_up_test_multi_board_run as test
        class_file = test.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.test_data_in_speed_up_test_multi_board_run.main  # NOQA
