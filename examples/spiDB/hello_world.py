"""
Hello World program on Spinnaker

Each core stores into its region in SDRAM the string:
"Hello World from $chip.x, $chip.y, $core"

We then fetch the written data and print it on the python console.

Author: Arthur Ceccotti
"""

import spynnaker_graph_front_end as front_end

from hello_world_vertex import HelloWorldVertex

from device_manager import DeviceManager

from spynnaker_external_devices_plugin.pyNN.connections\
    .spynnaker_live_spikes_connection import SpynnakerLiveSpikesConnection

from spynnaker_external_devices_plugin.pyNN.connections\
    .spynnaker_live_spikes_connection import LiveEventConnection

from spinn_front_end_common.utilities.database.database_connection \
    import DatabaseConnection

from spinnman.messages.eieio.data_messages.eieio_16bit\
    .eieio_16bit_data_message import EIEIO16BitDataMessage
from spinnman.messages.eieio.data_messages.eieio_32bit\
    .eieio_32bit_data_message import EIEIO32BitDataMessage
from spinnman.connections.connection_listener import ConnectionListener
from spinnman.connections.udp_packet_connections.udp_eieio_connection \
    import UDPEIEIOConnection

from spinnman.messages.eieio.eieio_type import EIEIOType

from spynnaker_external_devices_plugin.pyNN.external_devices_models.\
    external_cochlea_device import ExternalCochleaDevice
from spynnaker_external_devices_plugin.pyNN.external_devices_models.\
    external_fpga_retina_device import ExternalFPGARetinaDevice
from spynnaker_external_devices_plugin.pyNN.external_devices_models.\
    munich_retina_device import MunichRetinaDevice
from spynnaker_external_devices_plugin.pyNN.external_devices_models.\
    pushbot_retina_device import PushBotRetinaDevice
from spynnaker_external_devices_plugin.pyNN.external_devices_models.\
    pushbot_retina_device import PushBotRetinaResolution
from spynnaker_external_devices_plugin.pyNN.external_devices_models.\
    pushbot_retina_device import PushBotRetinaPolarity
from spynnaker_external_devices_plugin.pyNN import model_binaries

from spynnaker_external_devices_plugin.pyNN.utility_models.spike_injector \
    import SpikeInjector as SpynnakerExternalDeviceSpikeInjector
from spynnaker_external_devices_plugin.pyNN.connections\
    .spynnaker_live_spikes_connection import SpynnakerLiveSpikesConnection

from spynnaker.pyNN.utilities import conf
from spynnaker.pyNN import IF_curr_exp
from spynnaker.pyNN.spinnaker import executable_finder


from spinn_front_end_common.utilities.notification_protocol.socket_address \
    import SocketAddress

from live_packet_connection import LivePacketConnection

import logging

#from spynnaker_external_devices_plugin.pyNN.connections\
#    .spynnaker_live_spikes_connection import SpynnakerLiveSpikesConnection

import os

# The maximum number of 32-bit keys that will fit in a packet
_MAX_FULL_KEYS_PER_PACKET = 63

# The maximum number of 16-bit keys that will fit in a packet
_MAX_HALF_KEYS_PER_PACKET = 127

logger = logging.getLogger(__name__)
listen_port = 19998
notify_port = 19999

front_end.setup(graph_label="hello_world", database_socket_addresses=[SocketAddress("localhost", notify_port, listen_port)],
                model_binary_module=file(os.getcwd() + "/../model_binaries/hello_world.aplx"))

spynnaker_external_devices = DeviceManager()

dimenions = front_end.get_machine_dimensions()

machine_time_step = 100
time_scale_factor = 1

machine_port = 11111
machine_recieve_port = 22222
machine_host = "0.0.0.0"

x_dimension = dimenions['x']+1
y_dimension = dimenions['y']+1
p_dimension = 18

# calculate total number of 'free' cores for the given board
# (ie. does not include those busy with sark or reinjection)
total_number_of_cores = (p_dimension-2) * x_dimension * y_dimension

total_number_of_cores = 1

vertices = list()

# fill all cores with a HelloWorldVertex each
for x_position in range(0, total_number_of_cores):
        v = front_end.add_partitioned_vertex(
            HelloWorldVertex,
            {'machine_time_step': machine_time_step,
             'time_scale_factor': time_scale_factor},
             label="Hello{}".format(x_position))
        vertices.append(v)

def send_input_forward(label, sender):
    logger.info("Sending packet")
    # neuron id!!!!!?!!?!!?!!?!?!?
    #sender.send_spike(label, 0, send_full_keys=True)


#activate_live_output_for(vertices[0], database_notify_host="localhost", database_notify_port_num=19996)
#conn = LivePacketConnection("conn", send_labels=["Hello0"])
#conn.add_start_callback("Hello0", send_input_forward)
#conn.send_event("Hello0", send_full_keys=False)


# TODO do I need 'activate_live_output_for' ???
#live_spikes_connection_send = SpynnakerLiveSpikesConnection(
#    receive_labels=None, local_port=19999,
#    send_labels=["Hello0"])

live_spikes_connection_send = SpynnakerLiveSpikesConnection(
    receive_labels=None, local_port=19999,
    send_labels=["Hello0"])

#live_spikes_connection_send = LiveEventConnection("HelloWorld", send_labels=["Hello0"])

live_spikes_connection_send.add_start_callback(
    "Hello0", send_input_forward)


front_end.run(10)
front_end.stop()