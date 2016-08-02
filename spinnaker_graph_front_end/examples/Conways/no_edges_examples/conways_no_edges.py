
import spinnaker_graph_front_end as front_end
import sys

from spinnaker_graph_front_end.examples.Conways.no_edges_examples.\
    conways_basic_cell import ConwayBasicCell

n_chips_required = 48

# set up the front end and ask for the detected machines dimensions
front_end.setup(
    graph_label="conway_graph", model_binary_module=sys.modules[__name__],
    n_chips_required=n_chips_required, time_scale_factor=1)

for count in range(0, 100):
    front_end.add_machine_vertex_instance(
        ConwayBasicCell("cell{}".format(count)))

front_end.run()
front_end.stop()
