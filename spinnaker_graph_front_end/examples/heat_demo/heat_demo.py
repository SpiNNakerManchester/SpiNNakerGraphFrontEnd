"""
heat demo main entrance allows users to run the heat demo on the tool chain
"""

from spinn_utilities.socket_address import SocketAddress

from pacman.model.constraints.placer_constraints\
    import PlacerChipAndCoreConstraint

# spinn front end common imports
from spinn_front_end_common.utility_models.live_packet_gather_machine_vertex \
    import LivePacketGatherMachineVertex
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
from _collections import defaultdict


def run_broken():
    machine_time_step = 1000
    time_scale_factor = 1
    machine_receive_port = 22222
    machine_host = "0.0.0.0"
    live_gatherer_label = "LiveHeatGatherer"
    notify_port = 19999
    database_listen_port = 19998

    n_chips_required = None
    if front_end.is_allocated_machine():
        n_chips_required = (5 * 48) + 1

    # set up the front end and ask for the detected machines dimensions
    front_end.setup(
        graph_label="heat_demo_graph",
        model_binary_module=sys.modules[__name__],
        database_socket_addresses={SocketAddress(
            "127.0.0.1", notify_port, database_listen_port)},
        n_chips_required=n_chips_required)
    machine = front_end.machine()

    # create a live gatherer vertex for each board
    default_gatherer = None
    live_gatherers = dict()
    used_cores = set()
    for chip in machine.ethernet_connected_chips:

        # Try to use core 17 if one is available as it is outside the grid
        processor = chip.get_processor_with_id(17)
        if processor is None or processor.is_monitor:
            processor = chip.get_first_none_monitor_processor()
        if processor is not None:
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
            live_gatherers[chip.x, chip.y] = live_gatherer
            used_cores.add((chip.x, chip.y, processor.processor_id))
            if default_gatherer is None:
                default_gatherer = live_gatherer

    # Create a list of lists of vertices (x * 4) by (y * 4)
    # (for 16 cores on a chip - missing cores will have missing vertices)
    max_x_element_id = (machine.max_chip_x + 1) * 4
    max_y_element_id = (machine.max_chip_y + 1) * 4
    vertices = [
        [None for _ in range(max_y_element_id)]
        for _ in range(max_x_element_id)
    ]

    receive_labels = list()
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
                        (chip_x, chip_y, core_p) not in used_cores):
                    element = front_end.add_machine_vertex(
                        HeatDemoVertex,
                        {
                            'machine_time_step': machine_time_step,
                            'time_scale_factor': time_scale_factor
                        },
                        label="Heat Element {}, {}".format(
                            x, y))
                    vertices[x][y] = element
                    vertices[x][y].add_constraint(
                        PlacerChipAndCoreConstraint(chip_x, chip_y, core_p))

                    # add a link from the heat element to the live packet
                    # gatherer
                    live_gatherer = live_gatherers.get(
                        (chip.nearest_ethernet_x, chip.nearest_ethernet_y),
                        default_gatherer)
                    front_end.add_machine_edge(
                        MachineEdge,
                        {
                            'pre_vertex': vertices[x][y],
                            'post_vertex': live_gatherer
                        },
                        label="Live output from {}, {}".format(x, y),
                        semantic_label="TRANSMISSION")
                    receive_labels.append(vertices[x][y].label)

    # build edges
    for x in range(0, max_x_element_id):
        for y in range(0, max_y_element_id):

            if vertices[x][y] is not None:

                # Add a north link if not at the top
                if ((y + 1) < max_y_element_id and
                        vertices[x][y + 1] is not None):
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
                if ((x + 1) < max_x_element_id and
                        vertices[x + 1][y] is not None):
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
        live_gatherer_label, receive_labels=receive_labels,
        local_port=notify_port, machine_vertices=True)
    heat_values = defaultdict(list)

    def receive_heat(label, atom, value):
        heat_values[label].append(value / 65536.0)

    # Set up callbacks to occur when spikes are received
    for label in receive_labels:
        live_heat_connection.add_receive_callback(label, receive_heat)

    front_end.run(1000)
    front_end.stop()

    for label in receive_labels:
        print "{}: {}".format(
            label, ["{:05.2f}".format(value) for value in heat_values[label]])

if __name__ == '__main__':
    run_broken()
