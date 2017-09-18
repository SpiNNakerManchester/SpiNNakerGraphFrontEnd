import struct
import traceback
import numpy

import spinnaker_graph_front_end as sim
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from pacman.model.graphs.machine import MachineEdge
from spinnaker_graph_front_end.examples.speed_tracker_with_protocol_search.\
    packet_gatherer_with_protocol import PacketGathererWithProtocol
from spinnaker_graph_front_end.examples.speed_tracker_with_protocol_search.\
    sdram_reader_and_transmitter_with_protocol import \
    SDRAMReaderAndTransmitterWithProtocol
import time
from spinnaker_graph_front_end.examples import \
    speed_tracker_with_protocol_search


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs, x, y):

        # setup system
        sim.setup(model_binary_module=speed_tracker_with_protocol_search)

        # build verts
        reader = SDRAMReaderAndTransmitterWithProtocol(mbs)
        reader.add_constraint(ChipAndCoreConstraint(x=x, y=y))
        receiver = PacketGathererWithProtocol()

        # add verts to graph
        sim.add_machine_vertex_instance(reader)
        sim.add_machine_vertex_instance(receiver)

        # build and add edge to graph
        sim.add_machine_edge_instance(
            MachineEdge(reader, receiver), "TRANSMIT")

        machine = sim.machine()
        if machine.is_chip_at(x, y):
            return self._do_run(reader, receiver, mbs)
        else:
            sim.stop()
            return None, False, False, ""

    @staticmethod
    def _do_run(reader, receiver, mbs):

        # run forever (to allow better speed testing)
        sim.run()

        # get placements for extraction
        placements = sim.placements()

        sim.transceiver().set_watch_dog(False)

        try:
            print "starting data gathering"
            start = float(time.time())
            data = receiver.get_data(
                sim.transceiver(),
                placements.get_placement_of_vertex(reader))
            end = float(time.time())
            # end sim
            sim.stop()

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

            # print data
            seconds = float(end - start)
            speed = (mbs * 8) / seconds
            print ("Read {} MB in {} seconds ({} Mb/s)".format(
                mbs, seconds, speed))
            return speed, True, False, ""

        except Exception as e:
            # if boomed. end so that we can get iobuf
            traceback.print_exc()
            sim.stop()
            return None, True, True, e.message


if __name__ == "__main__":

    # entry point for doing speed search
    data_sizes = [1, 2, 5, 10, 20, 30, 50, 100]
    locations = [(0, 0), (1, 1), (0, 3), (2, 4), (4, 0), (7, 7)]
    iterations_per_type = 100
    runner = Runner()

    data_times = dict()
    overall_data_times = list()
    failed_to_run_states = list()

    for mbs_to_run in data_sizes:
        for x_coord, y_coord in locations:
            for iteration in range(0, iterations_per_type):
                print "######################################################################"
                print "running {}:{}:{}:{}".format(mbs_to_run, x_coord, y_coord, iteration)
                print "######################################################################"
                speed_of_data_extraction, ran, blew_up, bang_message = \
                    runner.run(mbs_to_run, x_coord, y_coord)
                if ran:
                    if blew_up:
                        print "sim for iteration {} for {} msb on chip " \
                              "{}:{} failed with {}".format(
                                   iteration, mbs_to_run, x_coord, y_coord,
                                   bang_message)
                    else:
                        if mbs_to_run not in data_times:
                            data_times[mbs_to_run] = dict()
                        if (x_coord, y_coord) not in data_times[mbs_to_run]:
                            data_times[mbs_to_run][(x_coord, y_coord)] = list()
                        data_times[mbs_to_run][(x_coord, y_coord)].append(
                            speed_of_data_extraction)
                        overall_data_times.append(speed_of_data_extraction)
                else:
                    failed_to_run_states.append((x_coord, y_coord))

    print failed_to_run_states

    # calculate average, max, min, sd per field, then total
    for mbs_to_run in data_sizes:
        for x_coord, y_coord in locations:
            speed_times = data_times[mbs_to_run][(x_coord, y_coord)]

            # calculate average
            total = numpy.average(speed_times)

            # max
            max = numpy.max(speed_times)

            # min
            min = numpy.min(speed_times)

            # sd
            sd = numpy.std(speed_times)

            print "for msb = {}, from chip {}:{} average speed = {} " \
                  "max speed = {} min speed = {} std = {}".format(
                mbs_to_run, x_coord, y_coord, total, max, min, sd)

    # total

    # average
    average = numpy.average(overall_data_times)
    # max
    max = numpy.max(overall_data_times)

    # min
    min = numpy.min(overall_data_times)

    # sd
    sd = numpy.std(overall_data_times)

    print "overall average speed = {} max speed = {} min speed = {} " \
          "std = {}".format(average, max, min, sd)