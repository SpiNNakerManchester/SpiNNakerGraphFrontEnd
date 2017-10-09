from spinnaker_graph_front_end.examples.Conways.no_edges_examples \
    import conways_no_edges
from spinnaker_graph_front_end.examples.Conways.one_no_graph_example \
    import conways_no_graph
from spinnaker_graph_front_end.examples.Conways.\
    partitioned_example_a_no_vis_no_buffer \
    import conways_partitioned as conways_partitioned_a
from spinnaker_graph_front_end.examples.Conways.\
    partitioned_example_b_no_vis_buffer \
    import conways_partitioned as conways_partitioned_b
from spinnaker_graph_front_end.examples.\
    Conways.partitioned_example_c_vis_buffer \
    import conways_partitioned as conways_partitioned_c


import unittest


class TestConwayExamples(unittest.TestCase):

    def test_one_no_graph(self):
        conways_no_graph.do_run()

    def test_conways_no_edges(self):
        conways_no_edges.do_run()

    def test_conways_partitioned_a(self):
        conways_partitioned_a.do_run()

    def test_conways_partitioned_b(self):
        conways_partitioned_b.do_run()

    def test_conways_partitioned_c(self):
        conways_partitioned_c.run_broken()
