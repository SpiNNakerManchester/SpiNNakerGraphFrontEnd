from __future__ import print_function
import struct
import time
import spinnaker_graph_front_end as sim
from data_specification.utility_calls import get_region_base_address_offset
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinnaker_graph_front_end.examples import \
    test_extra_monitor_core_data_extraction_multiple_locations
from spinnaker_graph_front_end.examples.\
    test_extra_monitor_core_data_extraction_multiple_locations.sdram_writer \
    import SDRAMWriter


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs, number_of_repeats):

        # setup system
        sim.setup(
            model_binary_module=(
                test_extra_monitor_core_data_extraction_multiple_locations),
            n_chips_required=49*2)

        # build vertices
        locs = [
            (0, 0), (2, 2), (7, 7), (3, 0), (1, 0), (0, 1), (3, 3), (4, 4),
            (5, 5), (3, 5), (4, 0), (7, 4),
            (8, 4), (4, 8), (11, 11), (11, 0), (0, 11), (6, 3), (0, 6)
            ]
        writers = list()

        for chip_x, chip_y in locs:
            writer = SDRAMWriter(
                mbs, constraint=ChipAndCoreConstraint(chip_x, chip_y))
            # add vertices to graph
            sim.add_machine_vertex_instance(writer)
            writers.append(writer)
        sim.run(12)

        # get placements for extraction
        placements = sim.placements()
        machine = sim.machine()
        for _ in range(0, number_of_repeats):
            for writer in writers:

                writer_placement = placements.get_placement_of_vertex(writer)
                writer_chip = \
                    machine.get_chip_at(writer_placement.x, writer_placement.y)
                writer_nearest_ethernet = machine.get_chip_at(
                    writer_chip.nearest_ethernet_x,
                    writer_chip.nearest_ethernet_y)

                extra_monitor_vertices = sim.globals_variables.\
                    get_simulator()._last_run_outputs[
                        'MemoryExtraMonitorVertices']
                extra_monitor_gatherers = sim.globals_variables.\
                    get_simulator()._last_run_outputs[
                        'MemoryMCGatherVertexToEthernetConnectedChipMapping']

                receiver = None
                gatherer = extra_monitor_gatherers[(writer_nearest_ethernet.x,
                                                    writer_nearest_ethernet.y)]
                for vertex in extra_monitor_vertices:
                    placement = placements.get_placement_of_vertex(vertex)
                    if (placement.x == writer_placement.x and
                            placement.y == writer_placement.y):
                        receiver = vertex

                start = float(time.time())

                gatherer.set_cores_for_data_extraction(
                    sim.transceiver(), extra_monitor_vertices, placements)
                data = gatherer.get_data(
                    sim.transceiver(),
                    placements.get_placement_of_vertex(receiver),
                    self._get_data_region_address(sim.transceiver(),
                                                  writer_placement),
                    writer.mbs_in_bytes)
                gatherer.unset_cores_for_data_extraction(
                    sim.transceiver(), extra_monitor_vertices, placements)
                end = float(time.time())

                print("time taken to extract {} MB is {}. MBS of {}".format(
                    mbs, end - start, (mbs * 8) / (end - start)))

                self._check_data(data)

    @staticmethod
    def _get_data_region_address(transceiver, placement):
        # Get the App Data for the core
        app_data_base_address = transceiver.get_cpu_information_from_core(
            placement.x, placement.y, placement.p).user[0]

        # Get the provenance region base address
        base_address_offset = get_region_base_address_offset(
            app_data_base_address, SDRAMWriter.DATA_REGIONS.DATA.value)
        base_address_buffer = transceiver.read_memory(
            placement.x, placement.y, base_address_offset, 4)
        _ONE_WORD = struct.Struct("<I")
        return _ONE_WORD.unpack_from(base_address_buffer)[0]

    @staticmethod
    def _check_data(data):
        # check data is correct here
        elements = len(data) / 4
        ints = struct.unpack("<{}I".format(elements), data)
        start_value = 0
        for value in ints:
            if value != start_value:
                print("should be getting {}, but got {}".format(
                    start_value, value))
                start_value = value + 1
            else:
                start_value += 1


if __name__ == "__main__":

    runner = Runner()
    runner.run(mbs=20, number_of_repeats=3)
