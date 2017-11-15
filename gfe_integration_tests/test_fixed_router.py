import os
import unittest


class TestFidedRouter(unittest.TestCase):

    def test_hello_world(self):
        import spinnaker_graph_front_end.examples.test_fixed_router as fr_dir
        class_file = fr_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print path
        os.chdir(path)
        import spinnaker_graph_front_end.examples.test_fixed_router.hello_world   # NOQA

    def test_hello_world_tr(self):
        import spinnaker_graph_front_end.examples.test_fixed_router as fr_dir
        class_file = fr_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print path
        os.chdir(path)
        import spinnaker_graph_front_end.examples.test_fixed_router_transmitter_reciever.hello_world   # NOQA

