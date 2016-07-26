
import spinnaker_graph_front_end as front_end
import sys

n_chips_required = 48

# set up the front end and ask for the detected machines dimensions
front_end.setup(
    graph_label="conway_graph", model_binary_module=sys.modules[__name__],
    n_chips_required=n_chips_required)

front_end.run()
front_end.stop()
