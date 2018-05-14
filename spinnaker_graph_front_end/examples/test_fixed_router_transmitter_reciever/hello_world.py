"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""

import logging
import os
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.hello_world.hello_world_vertex import (
    HelloWorldVertex)
from spinnaker_graph_front_end.examples.test_fixed_router.\
    hello_world_vertex_clone import (
        HelloWorldVertexClone)

logger = logging.getLogger(__name__)

front_end.setup(n_chips_required=None, model_binary_folder=os.getcwd())
front_end.globals_variables.get_simulator().update_extra_mapping_inputs(
    {"FixedRouteDestinationClass": HelloWorldVertexClone})

# fill all cores with a HelloWorldVertex each
front_end.add_machine_vertex_instance(
    HelloWorldVertex(
        label="transmitter", constraints=[ChipAndCoreConstraint(x=1, y=1)]))
front_end.add_machine_vertex_instance(
    HelloWorldVertexClone(label="the clone!", constraints=[
        ChipAndCoreConstraint(x=0, y=0)]))

front_end.run(10)

front_end.stop()
