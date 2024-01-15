# Copyright (c) 2023 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from time import sleep
from random import randint
from pacman.model.graphs.machine.machine_edge import MachineEdge
from spinn_front_end_common.data.fec_data_view import FecDataView
from spinn_front_end_common.utilities.connections import LiveEventConnection
from spinn_front_end_common.utility_models import (
    EIEIOParameters, LivePacketGatherMachineVertex,
    ReverseIPTagMulticastSourceMachineVertex)
from spinn_front_end_common.utilities.utility_objs import (
    LivePacketGatherParameters)
import spinnaker_graph_front_end as front_end
from gfe_examples.live_io.live_io_vertex import LiveIOVertex

n_receivers = 20
receiver_label = "Receiver"
sender_label = "Sender"
sender_partition = "Send"
n_sender_keys = 32
sends_per_cycle = 10
lpg_label = "LPGReceiver"
running = True


def start_sending(label, c):
    # pylint: disable=unused-argument
    sleep(0.5)
    while running:
        for _ in range(sends_per_cycle):
            key = randint(0, n_sender_keys - 1)
            print(f"Sending {key}")
            c.send_event(sender_label, key)
        sleep(0.1)


def end_sim(label, c):
    # pylint: disable=unused-argument,global-statement
    global running
    running = False


def receive(label, time, keys):
    print(f"Received from {label} at time {time}: {keys}")


# Make a connection to send and receive data
conn = LiveEventConnection(
    live_packet_gather_label=lpg_label,
    receive_labels=[receiver_label + f" {x}" for x in range(n_receivers)],
    send_labels=[sender_label], local_port=None)
conn.add_start_resume_callback(sender_label, start_sending)
conn.add_pause_stop_callback(sender_label, end_sim)
for x in range(n_receivers):
    conn.add_receive_callback(receiver_label + f" {x}", receive)

front_end.setup(
    n_chips_required=1, model_binary_folder=os.path.dirname(__file__))
front_end.add_socket_address(None, None, conn.local_port)

# Add a sender
eieio_params = EIEIOParameters(injection_partition_id=sender_partition)
sender = ReverseIPTagMulticastSourceMachineVertex(
    n_keys=n_sender_keys, label="Sender",
    eieio_params=eieio_params)
front_end.add_machine_vertex_instance(sender)

live_out = LivePacketGatherMachineVertex(
    LivePacketGatherParameters(tag=1, port=10000, hostname="localhost"),
    label=lpg_label)
front_end.add_machine_vertex_instance(live_out)


# Put LiveIOVertex on some cores
for x in range(n_receivers):
    vertex = LiveIOVertex(
        n_keys=n_sender_keys, send_partition=sender_partition,
        label=receiver_label + f" {x}")
    front_end.add_machine_vertex_instance(vertex)
    front_end.add_machine_edge_instance(
        MachineEdge(sender, vertex), sender_partition)
    front_end.add_machine_edge_instance(
        MachineEdge(vertex, live_out), sender_partition)
    live_out.add_incoming_source(vertex, sender_partition)
    FecDataView.add_live_output_vertex(vertex, sender_partition)

front_end.run(10000)

front_end.stop()
