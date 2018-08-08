"""
connectivity tester for SpiNNaker 2
"""
import spinnaker_graph_front_end as front_end

import logging
import numpy
import math
from scipy.spatial.distance import cdist

from pacman.model.graphs.machine import MachineEdge
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinnaker_graph_front_end.examples.spinnaker_2_vm_network_tests.\
    space_taker_machine_vertex import SpaceTakerMachineVertex
from spinn_utilities.progress_bar import ProgressBar

numpy.set_printoptions(threshold=numpy.nan, linewidth=1000000)

logger = logging.getLogger(__name__)

EXP_CONSTANT = 10.0
NETWORK_WIDTH = 80
NETWORK_HEIGHT = 80

front_end.setup()
config = front_end.get_config()
n_cores_per_chip = config.getint("Machine", "NCoresPerChip") - 1
n_cores_square = int(math.sqrt(n_cores_per_chip))

logger.info("Building vertices")
verts = list()
for x in xrange(NETWORK_WIDTH):
    for y in xrange(NETWORK_HEIGHT):
        vertex = SpaceTakerMachineVertex(x, y)
        chip_x = x // n_cores_square
        chip_y = y // n_cores_square
        vertex.add_constraint(ChipAndCoreConstraint(chip_x, chip_y))
        front_end.add_machine_vertex_instance(vertex)
        verts.append(vertex)

# Get the coordinates
logger.info("Working out connections")
coordinates = numpy.array([[v.x, v.y] for v in verts])

# Find the distances between vertices
distances = cdist(coordinates, coordinates, metric="cityblock")

# Decide which connections exist based on the distances
metric = numpy.exp(-distances / EXP_CONSTANT)
randoms = numpy.random.random(metric.shape)
connections_to_make = metric >= randoms

# Get combinations of coordinates
indices = numpy.arange(len(coordinates))
combinations = numpy.array(verts)[
    numpy.stack(numpy.meshgrid(indices, indices)).T]

# Get the connections actually made
connections = combinations[connections_to_make]

# Display a useful histogram of connections made by distance
connections_possible = numpy.bincount(distances.flatten().astype("int64"))
connections_made = numpy.bincount(
    distances[connections_to_make].astype("int64"),
    minlength=len(connections_possible))
print numpy.true_divide(connections_made, connections_possible)

# fill in edges
progress = ProgressBar(len(connections), "Building {} of {} Edges"
                       .format(len(connections),
                               len(combinations) ** 2))
for (v1, v2) in connections:
    front_end.add_machine_edge_instance(
        MachineEdge(v1, v2), "ConnectivityTest")
    progress.update()
progress.end()

logger.info("setting off run")
front_end.run(10)
front_end.stop()
