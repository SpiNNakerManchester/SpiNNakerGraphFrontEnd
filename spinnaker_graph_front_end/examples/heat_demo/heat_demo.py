"""
heat demo main entrance allows users to run the heat demo on the tool chain
"""

from pacman.model.constraints.placer_constraints\
    .placer_chip_and_core_constraint import PlacerChipAndCoreConstraint

# spinn front end common imports
from spinn_front_end_common.utility_models.\
    live_packet_gather_machine_vertex import \
    LivePacketGatherMachineVertex
from threading import Condition
from spinn_front_end_common.utilities.notification_protocol.socket_address \
    import SocketAddress
from spinn_front_end_common.utilities.connections.live_event_connection \
    import LiveEventConnection

# SpiNNMan imports
from spinnman.messages.eieio.eieio_type import EIEIOType

# graph front end imports
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end import MachineEdge

# example imports
from spinnaker_graph_front_end.examples.heat_demo.heat_demo_vertex\
    import HeatDemoVertex
from spinnaker_graph_front_end.examples.heat_demo.heat_demo_edge\
    import HeatDemoEdge

import sys

machine_time_step = 1000
time_scale_factor = 1
machine_port = 11111
machine_receive_port = 22222
machine_host = "0.0.0.0"
live_gatherer_label = "LiveHeatGatherer"
notify_port = 19999
database_listen_port = 19998

n_chips_required = None
if front_end.is_allocated_machine():
    n_chips_required = 2


# set up the front end and ask for the detected machines dimensions
front_end.setup(
    graph_label="heat_demo_graph", model_binary_module=sys.modules[__name__],
    database_socket_addresses={SocketAddress(
        "127.0.0.1", notify_port, database_listen_port)},
    n_chips_required=n_chips_required)
machine = front_end.machine()

# Create a gatherer to read the heat values
live_gatherer = front_end.add_machine_vertex(
    LivePacketGatherMachineVertex,
    {
        'label': live_gatherer_label,
        'ip_address': machine_host,
        'port': machine_receive_port,
        'payload_as_time_stamps': False,
        'use_payload_prefix': False,
        'strip_sdp': True,
        'message_type': EIEIOType.KEY_PAYLOAD_32_BIT
    }
)
live_gatherer.add_constraint(PlacerChipAndCoreConstraint(0, 0, 1))

# Create a list of lists of vertices (x * 4) by (y * 4)
# (for 16 cores on a chip - missing cores will have missing vertices)
max_x_element_id = 2 * 4
max_y_element_id = 2 * 4
vertices = [
    [None for j in range(max_y_element_id)]
    for i in range(max_x_element_id)
]
for x in range(0, max_x_element_id):
    for y in range(0, max_y_element_id):

        chip_x = x / 4
        chip_y = y / 4
        core_x = x % 4
        core_y = y % 4
        core_p = ((core_x * 4) + core_y) + 1

        # Add an element if the chip and core exists
        chip = machine.get_chip_at(chip_x, chip_y)
        if chip is not None:
            core = chip.get_processor_with_id(core_p)
            if (core is not None and not core.is_monitor and
                    not (chip_x == 0 and chip_y == 0 and core_p == 1)):
                element = front_end.add_machine_vertex(
                    HeatDemoVertex,
                    {
                        'machine_time_step': machine_time_step,
                        'time_scale_factor': time_scale_factor
                    },
                    label="Heat Element {}, {}".format(
                        x, y))
                vertices[x][y] = element
                vertices[x][y].add_constraint(PlacerChipAndCoreConstraint(
                    chip_x, chip_y, core_p))

# build edges
receive_labels = list()
for x in range(0, max_x_element_id):
    for y in range(0, max_y_element_id):

        if vertices[x][y] is not None:

            # add a link from the heat element to the live packet gatherer
            front_end.add_machine_edge(
                MachineEdge,
                {
                    'pre_vertex': vertices[x][y],
                    'post_vertex': live_gatherer
                },
                label="Live output from {}, {}".format(x, y),
                semantic_label="TRANSMISSION")
            receive_labels.append(vertices[x][y].label)

            # Add a north link if not at the top
            if (y + 1) < max_y_element_id and vertices[x][y + 1] is not None:
                front_end.add_machine_edge(
                    HeatDemoEdge,
                    {
                        'pre_vertex': vertices[x][y],
                        'post_vertex': vertices[x][y + 1],
                        'direction': HeatDemoEdge.DIRECTIONS.SOUTH
                    },
                    label="North Edge from {}, {} to {}, {}".format(
                        x, y, x + 1, y),
                    semantic_label="TRANSMISSION")

            # Add an east link if not at the right
            if (x + 1) < max_y_element_id and vertices[x + 1][y] is not None:
                front_end.add_machine_edge(
                    HeatDemoEdge,
                    {
                        'pre_vertex': vertices[x][y],
                        'post_vertex': vertices[x + 1][y],
                        'direction': HeatDemoEdge.DIRECTIONS.WEST
                    },
                    label="East Edge from {}, {} to {}, {}".format(
                        x, y, x + 1, y),
                    semantic_label="TRANSMISSION")

            # Add a south link if not at the bottom
            if (y - 1) >= 0 and vertices[x][y - 1] is not None:
                front_end.add_machine_edge(
                    HeatDemoEdge,
                    {
                        'pre_vertex': vertices[x][y],
                        'post_vertex': vertices[x][y - 1],
                        'direction': HeatDemoEdge.DIRECTIONS.NORTH
                    },
                    label="South Edge from {}, {} to {}, {}".format(
                        x, y, x, y - 1),
                    semantic_label="TRANSMISSION")

            # check for the likely hood for a W link
            if (x - 1) >= 0 and vertices[x - 1][y] is not None:
                front_end.add_machine_edge(
                    HeatDemoEdge,
                    {
                        'pre_vertex': vertices[x][y],
                        'post_vertex': vertices[x - 1][y],
                        'direction': HeatDemoEdge.DIRECTIONS.EAST
                    },
                    label="West Edge from {}, {} to {}, {}".format(
                        x, y, x - 1, y),
                    semantic_label="TRANSMISSION")


# Set up the live connection for receiving heat elements
live_heat_connection = LiveEventConnection(
    live_gatherer_label, receive_labels=receive_labels, local_port=notify_port,
    machine_vertices=True)
condition = Condition()


def receive_heat(label, atom, value):
    condition.acquire()
    print "{}: {}".format(label, value / 65536.0)
    condition.release()


# Set up callbacks to occur when spikes are received
for label in receive_labels:
    live_heat_connection.add_receive_callback(label, receive_heat)

front_end.run(1000)
front_end.stop()
