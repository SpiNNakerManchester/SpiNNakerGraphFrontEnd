"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.
"""
from pacman.model.graphs.machine import MachineEdge

import logging
import os
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.hello_world.hello_world_vertex import (
    HelloWorldVertex)

logger = logging.getLogger(__name__)

# Kostas: Based on the ppt GFE , here we read the cfg parameters and create every
# object that is needed.
front_end.setup(
    # Kostas: the binary file is the hello_world.aplx
    n_chips_required=None, model_binary_folder=os.path.dirname(__file__))

helloWorldList = []
nEdges = 2

print("add_machine_vertex_instance")

# fill all cores with a HelloWorldVertex each
# Kostas: add the vertices to each core, the description is clear.
for x in range(0, nEdges):
    helloWorldInstanse = HelloWorldVertex("Hello World at x {}".format(x))
    helloWorldList.append(helloWorldInstanse)
    front_end.add_machine_vertex_instance(helloWorldInstanse)


print("adds edges")
# Kostas : adds edges
for x in range(0, nEdges):
    # print("hello world x is ",helloWorldList[x] , helloWorldList[(x+1) % nEdges] )
    front_end.add_machine_edge_instance(
        MachineEdge( helloWorldList[x], helloWorldList[(x+1) % nEdges],
                     label=x), "TEST")

print("run simulation")
# Kostas: run the simulation for a given time period
front_end.run(10)

placements = front_end.placements()
buffer_manager = front_end.buffer_manager()
print("buffer_manager is %s" % buffer_manager)

print("read the SDRAM after the simulation run")
for placement in sorted(placements.placements,
                        key=lambda p: (p.x, p.y, p.p)):
    # Kostas : After the run of the simulation, read
    # from SDRAM all the texts that were stored in SDRAM.
    if isinstance(placement.vertex, HelloWorldVertex):
        hello_world = placement.vertex.read(placement, buffer_manager)
        logger.info("{}, {}, {} > {}".format(
            placement.x, placement.y, placement.p, hello_world))

# Kostas: closes down any application that is running on spinnaker and does housekeeping
# to let new applications to run.
front_end.stop()
