"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.

Author: Arthur Ceccotti
"""

import logging

import spynnaker_graph_front_end as front_end
from slave.slave_vertex import SlaveVertex
from master.master_vertex import MasterVertex
from boss.boss_vertex import BossVertex

from spinn_front_end_common.utilities.notification_protocol.socket_address \
    import SocketAddress

from spynnaker_external_devices_plugin.pyNN.connections\
    .spynnaker_live_spikes_connection import SpynnakerLiveSpikesConnection

from spinnman.messages.eieio.command_messages.eieio_command_header\
    import EIEIOCommandHeader

from spike_send_thread import SpikeSendThread

import os

# The maximum number of 32-bit keys that will fit in a packet
_MAX_FULL_KEYS_PER_PACKET = 63

# The maximum number of 16-bit keys that will fit in a packet
_MAX_HALF_KEYS_PER_PACKET = 127

logger = logging.getLogger(__name__)
listen_port = 19998
notify_port = 19999

# database_socket_addresses=[SocketAddress("localhost", notify_port, listen_port)],

front_end.setup(graph_label="spiDB",
                model_binary_modules=[file(os.getcwd() + "/../model_binaries/slave.aplx"),
                                      file(os.getcwd() + "/../model_binaries/master.aplx")])

#spynnaker_external_devices = DeviceManager()

#dimenions = front_end.get_machine_dimensions() #todo with the new changes this gets broken

machine_time_step = 100
time_scale_factor = 1

machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"

#x_dimension = dimenions['x']+1
#y_dimension = dimenions['y']+1

x_dimension = 1
y_dimension = 1
p_dimension = 18

# calculate total number of 'free' cores for the given board
# (ie. does not include those busy with sark or reinjection)

#total_number_of_slaves = (p_dimension-2) * x_dimension * y_dimension

total_number_of_slaves = 15

vertices = list()

master_vertex = front_end.add_partitioned_vertex(
    BossVertex,
    {'label': 'Boss',
     'machine_time_step': machine_time_step,
     'time_scale_factor': time_scale_factor,
     'port': machine_port},
    label="Boss")

for x_position in range(0, total_number_of_slaves):
        v = front_end.add_partitioned_vertex(
            SlaveVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="Slave{}".format(x_position))
        vertices.append(v)


#TODO not from 0 to 3 hardcoded
#TODO LABELS
for c in range(0, 3):
    master_vertex = front_end.add_partitioned_vertex(
        MasterVertex,
        {'label': 'Master',
         'machine_time_step': machine_time_step,
         'time_scale_factor': time_scale_factor},
        label="Master{}".format(c))
    vertices.append(master_vertex)


    for x_position in range(0, total_number_of_slaves):
            v = front_end.add_partitioned_vertex(
                SlaveVertex,
                {'machine_time_step': machine_time_step,
                 'time_scale_factor': time_scale_factor},
                 label="Slave{}".format(x_position))
            vertices.append(v)



def init_callback_master():
    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ INIT CALLBACK ------ MASTER")

def start_callback_master():
    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ START CALLBACK ----- MASTER")

# look at spike_io.py
# look at heat_demo.py

#c = DB_PacketConn(remote_host="192.168.240.253", remote_port=54321)

#c.send(EIEIOCommandHeader(1).bytestring)

#activate_live_output_for(master_vertex, database_notify_host="localhost",
#                         database_notify_port_num=19996)

sst = SpikeSendThread()

"""
# Set up the live connection for sending spikes
live_spikes_connection_send = SpynnakerLiveSpikesConnection(
    receive_labels=None, local_port=19999,
    send_labels=["Master"])


#19999
live_spikes_connection_send = DbLiveEventConnection(
    receive_labels=None, local_port=19996, local_host="localhost",
    send_labels=["Master"])

# Set up callbacks to occur at initialisation
live_spikes_connection_send.add_init_callback(
    "Master", init_callback_master)

# Set up callbacks to occur at the start of simulation
live_spikes_connection_send.add_start_callback(
    "Master", start_callback_master)
"""
front_end.run(100)
front_end.stop()