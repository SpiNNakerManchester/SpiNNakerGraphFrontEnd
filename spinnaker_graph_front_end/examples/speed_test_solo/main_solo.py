import struct
import traceback

import spinnaker_graph_front_end as sim
import time
from spinnaker_graph_front_end.examples import speed_test_solo

# data to write
from spinnaker_graph_front_end.examples.speed_test_solo.\
    packet_gatherer_cheat import PacketGathererCheat

mbs = 1.0

# setup system
sim.setup(model_binary_module=speed_test_solo)

# build verts
receiver = PacketGathererCheat(mbs, 1)

# add verts to graph
sim.add_machine_vertex_instance(receiver)

# run forever (to allow better speed testing)
sim.run()

# get placements for extraction
placements = sim.placements()

# try getting data via mc transmission
start = None
end = None
data = None

sim.transceiver().set_watch_dog(False)

try:
    print "starting data gathering"
    start = float(time.time())
    data = receiver.get_data(
        sim.transceiver(),
        placements.get_placement_of_vertex(receiver))
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
   # print ints
    for value in ints:
        if value != start_value:
            print "should be getting {}, but got {}".format(start_value, value)
            start_value = value + 1
        else:
            start_value += 1

except Exception as e:
    # if boomed. end so that we can get iobuf
    traceback.print_exc()


