import struct

import spinnaker_graph_front_end as sim
from data_specification.utility_calls import get_region_base_address_offset
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinnaker_graph_front_end.examples import \
    test_extra_monitor_core_data_extraction
from spinnaker_graph_front_end.examples.\
    test_extra_monitor_core_data_extraction.sdram_writer import SDRAMWriter


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs):

        # setup system
        sim.setup(model_binary_module=test_extra_monitor_core_data_extraction,
                  n_chips_required=2)

        # build verts
        writer = SDRAMWriter(
            mbs, constraints=[ChipAndCoreConstraint(x=1, y=1)])

        # add verts to graph
        sim.add_machine_vertex_instance(writer)

        sim.run(12)

        # get placements for extraction
        placements = sim.placements()
        machine = sim.machine()

        writer_placement = placements.get_placement_of_vertex(writer)
        writer_chip = \
            machine.get_chip_at(writer_placement.x, writer_placement.y)
        writer_nearest_ethernet = machine.get_chip_at(
            writer_chip.nearest_ethernet_x, writer_chip.nearest_ethernet_y)

        extra_monitor_vertices = sim.globals_variables.\
            get_simulator()._last_run_outputs['MemoryExtraMonitorVertices']
        extra_monitor_ethernet_chips = sim.globals_variables.\
            get_simulator()._last_run_outputs[
            'MemoryExtraMonitorVertexToEthernetConnectedChipMapping']

        receiver = None
        gatherer = extra_monitor_ethernet_chips[
            (writer_nearest_ethernet.x, writer_nearest_ethernet.y)]
        for vertex in extra_monitor_vertices:
            placement = placements.get_placement_of_vertex(vertex)
            if (placement.x == writer_placement.x and
                    placement.y == writer_placement.y):
                receiver = vertex

        data, _ = gatherer.get_data(
            sim.transceiver(), placements.get_placement_of_vertex(receiver),
            self._get_data_region_address(sim.transceiver(), writer_placement),
            writer.mbs_in_bytes, extra_monitor_vertices, placements)

        self._check_data(data)

    @staticmethod
    def _get_data_region_address(transceiver, placement):
        # Get the App Data for the core
        app_data_base_address = transceiver.get_cpu_information_from_core(
            placement.x, placement.y, placement.p).user[0]

        # Get the provenance region base address
        base_address_offset = get_region_base_address_offset(
            app_data_base_address, SDRAMWriter.DATA_REGIONS.DATA.value)
        base_address_buffer = buffer(transceiver.read_memory(
            placement.x, placement.y, base_address_offset, 4))
        _ONE_WORD = struct.Struct("<I")
        return _ONE_WORD.unpack(str(base_address_buffer))[0]

    @staticmethod
    def _check_data(data):
        # check data is correct here
        elements = len(data) / 4
        ints = struct.unpack("<{}I".format(elements), data)
        start_value = 0
        for value in ints:
            if value != start_value:
                print "should be getting {}, but got {}".format(
                    start_value, value)
                start_value = value + 1
            else:
                start_value += 1


if __name__ == "__main__":

    runner = Runner()
    runner.run(mbs=20)
