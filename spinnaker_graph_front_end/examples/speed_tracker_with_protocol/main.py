import struct
import traceback

import spinnaker_graph_front_end as sim
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from pacman.model.graphs.machine import MachineEdge
from spinnaker_graph_front_end.examples.speed_tracker_with_protocol.\
    packet_gatherer_with_protocol import \
    PacketGathererWithProtocol
from spinnaker_graph_front_end.examples.speed_tracker_with_protocol.\
    sdram_reader_and_transmitter_with_protocol import \
    SDRAMReaderAndTransmitterWithProtocol
import time
from spinnaker_graph_front_end.examples import speed_tracker

# data to write
mbs = 20.0

# setup system
sim.setup(model_binary_module=speed_tracker)

# build verts
reader = SDRAMReaderAndTransmitterWithProtocol(mbs)
reader.add_constraint(ChipAndCoreConstraint(x=1, y=1))
receiver = PacketGathererWithProtocol()

# add verts to graph
sim.add_machine_vertex_instance(reader)
sim.add_machine_vertex_instance(receiver)

# build and add edge to graph
sim.add_machine_edge_instance(MachineEdge(reader, receiver), "TRANSMIT")

# run forever (to allow better speed testing)
sim.run()

# get placements for extraction
placements = sim.placements()

# try getting data via mc transmission
start = None
end = None
data = None

try:
    print "starting data gathering"
    start = float(time.time())
    data = receiver.get_data(
        sim.transceiver(),
        placements.get_placement_of_vertex(reader))
    end = float(time.time())
    # end sim
    sim.stop()

    # print data
    seconds = float(end - start)
    speed = (mbs * 8) / seconds
    print ("Read {} MB in {} seconds ({} Mb/s)".format(mbs, seconds, speed))

    # check data is correct here
    elements = len(data) / 4
    ints = struct.unpack("<{}I".format(elements), data)
    start_value = 0
    for value in ints:
        if value != start_value:
            print "should be getting {}, but got {}".format(start_value, value)
            start_value = value + 1
        else:
            start_value += 1


except Exception as e:
    # if boomed. end so that we can get iobuf
    traceback.print_exc()

