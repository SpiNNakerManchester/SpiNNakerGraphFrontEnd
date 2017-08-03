import struct

from enum import Enum

from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, SDRAMResource, \
    IPtagResource
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.utilities.utility_objs import ExecutableStartType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinnman.connections.udp_packet_connections import UDPConnection
from spinnman.exceptions import SpinnmanTimeoutException
from spinnman.messages.sdp import SDPMessage, SDPHeader, SDPFlag

import math


class PacketGathererCheat(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1)])
    PORT = 11111
    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024*1024
    CONFIG_SIZE = 8
    DATA_PER_FULL_PACKET = 63

    def __init__(self, mbs, add_seq):
        self._mbs = mbs * self.SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        MachineVertex.__init__(self, label="pg", constraints=None)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        self._view = None
        self._add_seq = add_seq

    @property
    def resources_required(self):
        return ResourceContainer(
            sdram=SDRAMResource(
                constants.SYSTEM_BYTES_REQUIREMENT + 4),
            iptags=[IPtagResource(port=self.PORT, strip_sdp=True,
                                  ip_address="localhost")])

    def get_binary_start_type(self):
        return ExecutableStartType.USES_SIMULATION_INTERFACE

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

    def get_data(self, transceiver, placement):
        data = struct.pack("<I", 100)
        print "sending to core {}:{}:{}".format(
            placement.x, placement.y, placement.p)
        message = SDPMessage(
            sdp_header=SDPHeader(
                destination_chip_x=placement.x,
                destination_chip_y=placement.y,
                destination_cpu=placement.p,
                destination_port=2,
                flags=SDPFlag.REPLY_NOT_EXPECTED),
            data=data)

        # create socket
        connection = UDPConnection(local_host=None, local_port=self.PORT)

        # send
        transceiver.send_sdp_message(message=message)

        # receive
        output = None
        finished = False
        first = True
        seq_num = 0
        seq_nums = list()
        while not finished:
            try:
                data = connection.receive(timeout=5)
                first, seq_num, seq_nums, finished= \
                    self._process_data(
                        data, first, seq_num, seq_nums, finished)
            except SpinnmanTimeoutException:
                self._transmit_missing_seq_nums(
                    seq_nums, transceiver, placement)

        self._check(seq_nums)
        return output

    def _transmit_missing_seq_nums(self, seq_nums, transceiver, placement):

        # locate missing seq nums from pile
        missing_seq_nums = list()
        seq_nums = sorted(seq_nums)
        last_seq_num = 0
        for seq_num in seq_nums:
            if seq_num != last_seq_num:
                missing_seq_nums.append(seq_num)
            last_seq_num = seq_num

        # transmit request for more info to sender.
        n_packets = int(math.ceil(
            (len(missing_seq_nums) * 4) / self.DATA_PER_FULL_PACKET - 1))

        # transmit missing seq as a new sdp packet
        first = True
        for packet_count in range(0, n_packets):

            data = struct.pack("<I", 1000)
            offset = 4

            # add n packets to packet, so c code can build SDRAM request
            if first:
                data = struct.pack_into("<I", data, offset, n_packets)
                offset += 4

            #




            message = SDPMessage(
                sdp_header=SDPHeader(
                    destination_chip_x=placement.x,
                    destination_chip_y=placement.y,
                    destination_cpu=placement.p,
                    destination_port=2,
                    flags=SDPFlag.REPLY_NOT_EXPECTED),
                data=data)
            transceiver.send_sdp_message(message=message)

    def _process_data(self, data, first, seq_num, seq_nums, finished):
        length_of_data = len(data)
        if first:
            length = struct.unpack_from("<I", data, 0)[0]
            print "length = {}".format(length)
            first = False
            output = bytearray(length)
            self._view = memoryview(output)
            self._view[0: length_of_data - 4] = data[4:4 + length_of_data - 4]

        else:
            first_packet_element = struct.unpack_from(
                "<I", data, 0)[0]
            last_mc_packet = struct.unpack_from(
                "<I", data, length_of_data - 4)[0]
            if self._add_seq:
                if first_packet_element != seq_num:
                    print "missing seq {}".format(seq_num)
                seq_num = first_packet_element
                seq_nums.append(seq_num)

            offset = seq_num * self.DATA_PER_FULL_PACKET
            if last_mc_packet == 0xFFFFFFFF:
                self._view[offset:offset + length_of_data - 4] = \
                    data[0:0 + length_of_data - 4]
                finished = True
            else:
                self._view[offset:offset + length_of_data] = \
                    data[0:0 + length_of_data]
        return first, seq_num, seq_nums, finished

    @staticmethod
    def _check(seq_nums):
        # hand back
        seq_nums = sorted(seq_nums)
        last_seq_num = 0
        if len(seq_nums) != 4096:
            print len(seq_nums)
        for seq_num in seq_nums:
            if seq_num != last_seq_num:
                print "missing seq num {}".format(seq_num)
            last_seq_num = seq_num
