"""
connecitvity tester for SpiNNaker 2 vm
"""
from collections import defaultdict

import spinnaker_graph_front_end as front_end

import logging
import os

from pacman.model.graphs.machine import MachineEdge
from spinnaker_graph_front_end.examples.spinnaker_2_vm_network_tests.\
    space_taker_machine_vertex import SpaceTakerMachineVertex

logger = logging.getLogger(__name__)

class ConnectivityTest(object):

    def run(self):
        front_end.setup(
            n_chips_required=None,
            model_binary_folder=os.path.dirname(__file__))

        # calculate total number of 'free' cores for the given board
        # (i.e. does not include those busy with SARK or reinjection)
        total_number_of_cores = \
            front_end.get_number_of_available_cores_on_machine()
        logger.info("building graph for machine with {} cores".format(
            total_number_of_cores))

        machine = front_end.machine()

        # fill all cores with a HelloWorldVertex each
        logger.info("building verts")
        verts = list()
        for chip in machine.chips:
            for processor in range(0, chip.n_user_processors - 4):
                vertex = SpaceTakerMachineVertex(x=chip.x, y=chip.y)
                front_end.add_machine_vertex_instance(vertex)
                verts.append(vertex)

        # fill in edges
        logger.info("building edges")
        for vertex_x in verts:
            for vertex_y in verts:
                if not self._determine_if_edge_needs_removing(
                        vertex_x.x, vertex_x.y, vertex_y.x, vertex_y.y,
                        machine):
                    front_end.add_machine_edge_instance(
                        MachineEdge(post_vertex=vertex_y, pre_vertex=vertex_x),
                        "ConnectivityTest")

        logger.info("setting off run")
        front_end.run(10)
        front_end.stop()

    def _determine_if_edge_needs_removing(
            self, pre_x, pre_y, post_x, post_y, machine):
        shortest_distance = self._calculate_shortest_distance(
            pre_x, pre_y, post_x, post_y, machine)
        return self._probability(shortest_distance)

    @staticmethod
    def _calculate_shortest_distance(
            source_x, source_y, dest_x, dest_y, machine):
        look_at = defaultdict(list)
        distance = dict()
        hop = -1
        look_at[0].append((source_x, source_y))
        distance[(source_x, source_y)] = 0
        while len(look_at[hop + 1]) > 0:
            hop += 1
            next_hop = hop + 1
            for (source_x, source_y) in look_at[hop]:
                for link in machine.get_chip_at(
                        source_x, source_y).router.links:
                    if (link.destination_x, link.destination_y) not in distance:
                        distance[
                            (link.destination_x,
                             link.destination_y)] = next_hop
                        look_at[next_hop].append(
                            (link.destination_x, link.destination_y))
                    if (link.destination_x == dest_x and
                            link.destination_y == dest_y):
                        return next_hop
        raise Exception("Didnt find the blasted chip")

    @staticmethod
    def _probability(shortest_distance):
        return False

if __name__ == "__main__":
    test = ConnectivityTest()
    test.run()
