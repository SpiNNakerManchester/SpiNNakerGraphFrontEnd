import struct
import traceback
import subprocess

import spinnaker_graph_front_end as sim
import time

from spinnaker_graph_front_end.examples import speed_test_solo
#from __builtin__ import None

from spinn_front_end_common.utilities import constants
#from spinnaker_graph_front_end.examples import speed_tracker_with_protocol_search_c_code_version
#from spinnaker_graph_front_end.examples.speed_tracker_with_protocol_search_c_code_version import host_data_receiver

from spinnaker_graph_front_end.examples.speed_test_solo.\
    packet_gatherer_cheat import PacketGathererCheat

from spinnman.messages.sdp import SDPMessage, SDPHeader, SDPFlag

sim.setup(model_binary_module=speed_test_solo)

mbs = 1.0

# build verts
receiver = PacketGathererCheat(mbs, 1)

# add verts to graph
sim.add_machine_vertex_instance(receiver)

sim.run()

placements = sim.placements()

start = None
end = None
data = None

sim.transceiver().set_watch_dog(False)

try:
    print "Starting data gathering"
    start = float(time.time())

    #Fake message to get the remote address
    message = SDPMessage(
            sdp_header=SDPHeader(
                destination_chip_x=placements.get_placement_of_vertex(receiver).x,
                destination_chip_y=placements.get_placement_of_vertex(receiver).y,
                destination_cpu=placements.get_placement_of_vertex(receiver).p,
                destination_port=0,
                flags=SDPFlag.REPLY_NOT_EXPECTED),
            data=data)



    p = subprocess.call(["./c_code/host_data_receiver",
                        str(sim.transceiver().scamp_connection_selector.get_next_connection(message).remote_ip_address),
                        str(11111),
                        str(placements.get_placement_of_vertex(receiver).x),
                        str(placements.get_placement_of_vertex(receiver).y),
                        str(placements.get_placement_of_vertex(receiver).p),
                        "./c_code/read.txt",
                        "./c_code/missing.txt"])

    #data = host_data_receiver.get_data(sim.transceiver().get_connections()._scamp_connection_selector(),
    #                constants.SDP_PORTS.EXTRA_MONITOR_CORE_DATA_SPEED_UP.value,
    #                placements.get_placement_of_vertex(receiver).x,
    #                placements.get_placement_of_vertex(receiver).y,
    #                placements.get_placement_of_vertex(receiver).p)
    end = float(time.time())

    sim.stop()

    seconds = float(end - start)

    #elements = len(data) / 4
    #ints = struct.unpack("<{}I".format(elements), data)
    #start_value = 0

    #for value in ints:
    #    if value != start_value:
    #        print "should be getting {}, but got {}".format(start_value, value)
    #        start_value = value + 1
    #    else:
    #        start_value += 1

except Exception as e:
    traceback.print_exc()