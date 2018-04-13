from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinnaker_graph_front_end.examples import test_data_in_multi_run
from spinnaker_graph_front_end.examples.test_data_in_multi_run.sdram_writer \
    import SDRAMWriter
from data_specification.utility_calls import get_region_base_address_offset
import spinnaker_graph_front_end as sim
import time
import struct


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs, x, y):

        # setup system
        sim.setup(model_binary_module=test_data_in_multi_run,
                  n_chips_required=2)

        # build verts
        reader = SDRAMWriter(mbs)
        reader.add_constraint(ChipAndCoreConstraint(x=x, y=y))

        # add verts to graph
        sim.add_machine_vertex_instance(reader)

        return self._do_run(mbs, reader)

    def _do_run(self, mbs, writer):

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
        extra_monitor_gatherers = sim.globals_variables.\
            get_simulator()._last_run_outputs[
                'MemoryMCGatherVertexToEthernetConnectedChipMapping']
        fixed_routes = sim.globals_variables.\
            get_simulator()._last_run_outputs['MemoryFixedRoutes']
        txrx = sim.globals_variables.\
            get_simulator()._last_run_outputs['MemoryTransceiver']

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
            txrx, extra_monitor_vertices, placements)
        data = gatherer.get_data(
            txrx, placements.get_placement_of_vertex(receiver),
            self._get_data_region_address(sim.transceiver(), writer_placement),
            writer.mbs_in_bytes, fixed_routes)
        gatherer.unset_cores_for_data_extraction(
            txrx, extra_monitor_vertices, placements)
        end = float(time.time())

        print "time taken to extract {} MB is {}. MBS of {}".format(
            mbs, end - start, (mbs * 8) / (end - start))

        self._check_data(data)

        with open("python_results_8_100", "a") as myfile:
            myfile.write("{}:{}\n".format(mbs,  (mbs * 8) / (end - start)))
        sim.stop()

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

    # entry point for doing speed search
    data_sizes = [1]
    # data_sizes = [1, 2, 5, 10, 20, 30, 50, 100]
    locations = [(7, 7)]
    # locations = [(0, 0), (1, 1), (0, 3), (2, 4), (4, 0), (7, 7)]
    iterations_per_type = 100
    runner = Runner()

    data_times = dict()
    overall_data_times = list()
    failed_to_run_states = list()
    lost_data_pattern = dict()

    for mbs_to_run in data_sizes:
        for x_coord, y_coord in locations:
            for iteration in range(0, iterations_per_type):
                print "###########################################" \
                      "###########################"
                print "running {}:{}:{}:{}".format(
                    mbs_to_run, x_coord, y_coord, iteration)
                print "##################################################" \
                      "####################"
                runner.run(mbs_to_run, x_coord, y_coord)