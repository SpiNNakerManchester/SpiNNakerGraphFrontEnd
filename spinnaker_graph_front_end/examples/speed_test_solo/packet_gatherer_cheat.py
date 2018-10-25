import struct

from enum import Enum

from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, SDRAMResource, \
    IPtagResource
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinnman.connections.udp_packet_connections import UDPConnection
from spinnman.exceptions import SpinnmanTimeoutException
from spinnman.messages.sdp import SDPMessage, SDPHeader, SDPFlag

import math
import time


class PacketGathererCheat(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1)])
    PORT = 11111
    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024*1024
    CONFIG_SIZE = 16
    DATA_PER_FULL_PACKET = 68  # 272 bytes as removed scp header
    DATA_PER_FULL_PACKET_WITH_SEQUENCE_NUM = DATA_PER_FULL_PACKET - 1
    WORD_TO_BYTE_CONVERTER = 4

    TIMEOUT_PER_RECEIVE_IN_SECONDS = 1
    TIME_OUT_FOR_SENDING_IN_SECONDS = 0.01

    SDP_PACKET_START_SENDING_COMMAND_ID = 100
    SDP_PACKET_START_MISSING_SEQ_COMMAND_ID = 1000
    SDP_PACKET_MISSING_SEQ_COMMAND_ID = 1001
    SDP_PACKET_PORT = 2
    SDP_RETRANSMISSION_HEADER_SIZE = 2

    END_FLAG = 0xFFFFFFFF
    END_FLAG_SIZE = 4
    SEQUENCE_NUMBER_SIZE = 4
    N_PACKETS_SIZE = 4
    LENGTH_OF_DATA_SIZE = 4

    def __init__(self, mbs, add_seq, port):
        self._mbs = mbs * self.SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        MachineVertex.__init__(self, label="pg", constraints=None)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        self._view = None
        self._add_seq = add_seq
        self._max_seq_num = None
        self._output = None
        self.tag = None
        self._port = port

    @property
    def resources_required(self):
        return ResourceContainer(
            sdram=SDRAMResource(
                constants.SYSTEM_BYTES_REQUIREMENT + 4),
            iptags=[IPtagResource(port=self._port, strip_sdp=True,
                                  ip_address="localhost")])

    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):
        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT

        # Create the data regions for hello world
        self._reserve_memory_regions(spec, setup_size)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        spec.switch_write_focus(self.DATA_REGIONS.CONFIG.value)
        spec.write_value(self._mbs)
        spec.write_value(self._add_seq)

        self.tag = iptags[0].tag
        spec.write_value(iptags[0].tag)

        spec.write_value(self._port)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=system_size,
            label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.CONFIG.value, size=self.CONFIG_SIZE,
            label='memory to write')

    def get_binary_file_name(self):
        return "packet_gatherer_cheat.aplx"

    def get_ip(self, transceiver, placement):

        message = SDPMessage(
            sdp_header=SDPHeader(
                destination_chip_x=placement.x,
                destination_chip_y=placement.y,
                destination_cpu=placement.p,
                destination_port=0,
                flags=SDPFlag.REPLY_NOT_EXPECTED),
            data=None)

        connection = transceiver.scamp_connection_selector.get_next_connection(message)

        return connection.remote_ip_address, connection.chip_x, connection.chip_y

    def get_iptag(self):
        return self.tag

    def get_port(self):
        return self.SP_PACKET_PORT