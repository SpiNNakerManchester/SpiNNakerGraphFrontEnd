import struct
import traceback

import spinnaker_graph_front_end as sim
import time
from spinnaker_graph_front_end.examples import speed_test_solo

# data to write
from spinnaker_graph_front_end.examples.speed_test_solo.\
    packet_gatherer_cheat import PacketGathererCheat
import subprocess

mbs = 10
n_threads = 1
recv_list = list()
# setup system
sim.setup(model_binary_module=speed_test_solo)

# build verts
for i in range(n_threads):
    recv_list.append(PacketGathererCheat(mbs, 1, i+1))

# add verts to graph
for i in range(n_threads):
    sim.add_machine_vertex_instance(recv_list[i])

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

    plist = []

    print "starting data gathering"

    placement = []
    ip = [0 for i in range(n_threads)]
    chip_x = [0 for i in range(n_threads)]
    chip_y = [0 for i in range(n_threads)]

    for i in range(n_threads):
        placement.append(placements.get_placement_of_vertex(recv_list[i]))
        ip[i], chip_x[i], chip_y[i] = recv_list[i].get_ip(sim.transceiver(), placement[i])

    start = float(time.time())

    for i in range(n_threads):
        plist.append(subprocess.Popen(["./host_data_receiver",
                                       str(ip[i]),
                                       str(i+1),
                                       str(placement[i].x),
                                       str(placement[i].y),
                                       str(placement[i].p),
                                       str("./fileout_"+str(i)+".txt"),
                                       str("./missing_"+str(i)+".txt"),
                                       str(mbs*1024*1024),
                                       "0",
                                       str(chip_x[i]),
                                       str(chip_y[i]),
                                       str(recv_list[i].get_iptag())]))

    for i in plist:
        i.wait()

    end = float(time.time())
    # end sim
    sim.stop()

    # print data
    seconds = float(end - start)
    speed = (n_threads * mbs * 8) / seconds
    print ("Read {} MB in {} seconds ({} Mb/s)".format(mbs*n_threads, seconds, speed))

    for i in range(n_threads):
        with open("fileout_"+str(i)+".txt", "r") as fp:
            data = fp.read()

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
