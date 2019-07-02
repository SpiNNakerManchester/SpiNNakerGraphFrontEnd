import struct
import time
import os
import spinnaker_graph_front_end as sim
from data_specification.utility_calls import get_region_base_address_offset
from gfe_integration_tests.test_extra_monitor.sdram_writer import SDRAMWriter

_ONE_WORD = struct.Struct("<I")


def get_data_region_address(transceiver, placement):
    # Get the App Data for the core
    app_data_base_address = transceiver.get_cpu_information_from_core(
        placement.x, placement.y, placement.p).user[0]

    # Get the provenance region base address
    base_address_offset = get_region_base_address_offset(
        app_data_base_address, SDRAMWriter.DATA_REGIONS.DATA.value)
    return _ONE_WORD.unpack(transceiver.read_memory(
        placement.x, placement.y, base_address_offset, _ONE_WORD.size))[0]


def check_data(data):
    # check data is correct here
    ints = struct.unpack("<{}I".format(len(data) // 4), data)
    start_value = 0
    for value in ints:
        if value != start_value:
            print("should be getting {}, but got {}".format(
                start_value, value))
            start_value = value + 1
        else:
            start_value += 1


def test_extra_monitor():
    mbs = 20

    # setup system
    sim.setup(model_binary_folder=os.path.dirname(__file__),
              n_chips_required=2)

    # build verts
    writer = SDRAMWriter(mbs)

    # add verts to graph
    sim.add_machine_vertex_instance(writer)

    sim.run(12)

    # get placements for extraction
    placements = sim.placements()
    machine = sim.machine()

    writer_placement = placements.get_placement_of_vertex(writer)
    writer_chip = machine.get_chip_at(writer_placement.x, writer_placement.y)
    writer_nearest_ethernet = machine.get_chip_at(
        writer_chip.nearest_ethernet_x, writer_chip.nearest_ethernet_y)

    extra_monitor_vertices = sim.globals_variables.\
        get_simulator()._last_run_outputs['MemoryExtraMonitorVertices']
    extra_monitor_gatherers = sim.globals_variables.\
        get_simulator()._last_run_outputs[
            'MemoryMCGatherVertexToEthernetConnectedChipMapping']

    receiver = None
    gatherer = extra_monitor_gatherers[(writer_nearest_ethernet.x,
                                        writer_nearest_ethernet.y)]

    for vertex in extra_monitor_vertices:
        plt = placements.get_placement_of_vertex(vertex)
        if (plt.x == writer_placement.x and plt.y == writer_placement.y):
            receiver = vertex

    start = float(time.time())

    with gatherer.streaming(
            extra_monitor_gatherers.values(), sim.transceiver(),
            extra_monitor_vertices, placements):
        data = gatherer.get_data(
            placements.get_placement_of_vertex(receiver),
            get_data_region_address(sim.transceiver(), writer_placement),
            writer.mbs_in_bytes, fixed_routes=None)

    end = float(time.time())

    print("time taken to extract {} MB is {}. MBS of {}".format(
        mbs, end - start, (mbs * 8) / (end - start)))

    check_data(data)

    sim.stop()
