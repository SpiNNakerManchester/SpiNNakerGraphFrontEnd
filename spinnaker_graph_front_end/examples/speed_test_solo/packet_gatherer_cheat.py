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
import time

class PacketGathererCheat(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1)])
    PORT = 11111
    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024*1024
    CONFIG_SIZE = 8
    DATA_PER_FULL_PACKET = 68  # 272 bytes as removed scp header
    WORD_TO_BYTE_CONVERTER = 4

    SDP_PACKET_START_SENDING_COMMAND_ID = 100
    SDP_PACKET_START_MISSING_SEQ_COMMAND_ID = 1000
    SDP_PACKET_MISSING_SEQ_COMMAND_ID = 1001
    SDP_PACKET_PORT = 2

    END_FLAG = 0xFFFFFFFF

    def __init__(self, mbs, add_seq):
        self._mbs = mbs * self.SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        MachineVertex.__init__(self, label="pg", constraints=None)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        self._view = None
        self._add_seq = add_seq
        self._max_seq_num = None
        self._output = None

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
        data = struct.pack("<I", self.SDP_PACKET_START_SENDING_COMMAND_ID)
        print "sending to core {}:{}:{}".format(
            placement.x, placement.y, placement.p)
        message = SDPMessage(
            sdp_header=SDPHeader(
                destination_chip_x=placement.x,
                destination_chip_y=placement.y,
                destination_cpu=placement.p,
                destination_port=self.SDP_PACKET_PORT,
                flags=SDPFlag.REPLY_NOT_EXPECTED),
            data=data)

        # create socket
        connection = UDPConnection(local_host=None, local_port=self.PORT)

        # send
        transceiver.send_sdp_message(message=message)

        # receive
        finished = False
        first = True
        seq_num = 1
        seq_nums = list()
        while not finished:
            try:
                data = connection.receive(timeout=5)
                first, seq_num, seq_nums, finished = \
                    self._process_data(
                        data, first, seq_num, seq_nums, finished, placement,
                        transceiver)
            except SpinnmanTimeoutException:
                if not finished:
                    print "trying to reclaim missing sdp packets"
                    self._transmit_missing_seq_nums(
                        seq_nums, transceiver, placement)

        self._check(seq_nums)
        return self._output

    def _transmit_missing_seq_nums(self, seq_nums, transceiver, placement):

        # transmit request for more info to sender.
        self._check(seq_nums)
        self._print_missing(seq_nums)

        # locate missing seq nums from pile
        missing_seq_nums = list()
        seq_nums = sorted(seq_nums)
        last_seq_num = 0
        for seq_num in seq_nums:
            if seq_num != last_seq_num + 1:
                missing_seq_nums.append(seq_num)
            last_seq_num = seq_num
        if last_seq_num < self._max_seq_num:
            for missing_seq_num in range(last_seq_num, self._max_seq_num):
                missing_seq_nums.append(missing_seq_num)
                print "im missing seq num {}".format(missing_seq_num)

        print "missing seq total is {} out of {}".format(
            len(missing_seq_nums), self._max_seq_num)
        n_packets = int(math.ceil(
            (len(missing_seq_nums) * self.WORD_TO_BYTE_CONVERTER) /
            ((self.DATA_PER_FULL_PACKET - 1) * self.WORD_TO_BYTE_CONVERTER)))
        print "have to send {} packets for all seq nums missing".format(
            n_packets)

        # transmit missing seq as a new sdp packet
        first = True
        seq_num_offset = 0
        for packet_count in range(0, n_packets):
            length_left_in_packet = self.DATA_PER_FULL_PACKET
            offset = 0

            # get left over space / data size
            size_of_data_left_to_transmit = min(
                length_left_in_packet, len(missing_seq_nums) - seq_num_offset)

            # build data holder accordingly
            data = bytearray(
                size_of_data_left_to_transmit * self.WORD_TO_BYTE_CONVERTER)

            # if first, add n packets to list
            if first:
                # pack flag and n packets
                struct.pack_into(
                    "<I", data, offset,
                    self.SDP_PACKET_START_MISSING_SEQ_COMMAND_ID)
                struct.pack_into(
                    "<I", data, self.WORD_TO_BYTE_CONVERTER, n_packets)

                # update state
                offset += 2 * self.WORD_TO_BYTE_CONVERTER
                length_left_in_packet -= 2
                first = False

            else: # just add data
                # pack flag
                struct.pack_into(
                    "<I", data, offset, self.SDP_PACKET_MISSING_SEQ_COMMAND_ID)
                offset += 1 * self.WORD_TO_BYTE_CONVERTER
                length_left_in_packet -= 1

            # fill data field
            struct.pack_into(
                "<{}I".format(length_left_in_packet), data, offset,
                *missing_seq_nums[
                    seq_num_offset:
                    seq_num_offset + length_left_in_packet])
            seq_num_offset += length_left_in_packet

            # build sdp message
            message = SDPMessage(
                sdp_header=SDPHeader(
                    destination_chip_x=placement.x,
                    destination_chip_y=placement.y,
                    destination_cpu=placement.p,
                    destination_port=self.SDP_PACKET_PORT,
                    flags=SDPFlag.REPLY_NOT_EXPECTED),
                data=str(data))

            # send message to core
            transceiver.send_sdp_message(message=message)

            # debug
            reread_data = struct.unpack("<{}I".format(
                int(math.ceil(len(data) / self.WORD_TO_BYTE_CONVERTER))),
                str(data))
            print "converted data back into readable form is {}".format(
                reread_data)

            # sleep for ensuring core doesnt lose packets
            time.sleep(0.01)
            print("send sdp packet with missing seq nums: {} of {}".format(
                packet_count, n_packets))

    def _process_data(self, data, first, seq_num, seq_nums, finished,
                      placement, transceiver):
        length_of_data = len(data)
        if first:
            length = struct.unpack_from("<I", data, 0)[0]
            print "length = {}".format(length)
            first = False
            self._output = bytearray(length)
            self._view = memoryview(self._output)
            self._write_into_view(0, length_of_data - 4, data,
                                  4, 4 + length_of_data - 4)

            # deduce max seq num for future use
            self._max_seq_num = int(math.ceil(
                length / (self.DATA_PER_FULL_PACKET *
                          self.WORD_TO_BYTE_CONVERTER)))
            print "max seq num is {}".format(self._max_seq_num)

        else:  # some data packet
            first_packet_element = struct.unpack_from(
                "<I", data, 0)[0]
            last_mc_packet = struct.unpack_from(
                "<I", data, length_of_data - 4)[0]

            # this flag can be dropped at some point
            if self._add_seq:
                seq_num = first_packet_element
                seq_nums.append(seq_num)

            # write excess data as required
            offset = seq_num * self.DATA_PER_FULL_PACKET
            print "offset = {} from seq num {}".format(offset, seq_num)
            if last_mc_packet == self.END_FLAG:
                self._write_into_view(offset, offset + length_of_data - 4,
                                      data, 0, 0 + length_of_data - 4)
                if not self._check(seq_nums):
                    self._transmit_missing_seq_nums(
                        placement=placement, transceiver=transceiver,
                        seq_nums=seq_nums)
                else:
                    finished = True

            else:
                self._write_into_view(offset, offset + length_of_data,
                                      data, 0, 0 + length_of_data)
        return first, seq_num, seq_nums, finished

    def _write_into_view(
            self, view_start_position, view_end_position,
            data, data_start_position, data_end_position):
        """ puts data into the view
        
        :param view_start_position: where in view to start
        :param view_end_position: where in view to end
        :param data: the data holder to write from
        :param data_start_position: where in data holder to start from
        :param data_end_position: where in data holder to end
        :return: 
        """
        self._view[view_start_position: view_end_position] = \
            data[data_start_position:data_end_position]

    def _check(self, seq_nums):
        # hand back
        seq_nums = sorted(seq_nums)
        max_needed = int(math.ceil((self._mbs / (
            self.DATA_PER_FULL_PACKET * self.WORD_TO_BYTE_CONVERTER))))
        if len(seq_nums) != max_needed:
            print "should have received {} sequence numbers, but received " \
                  "{} sequence numbers".format(max_needed, len(seq_nums))
            return False
        return True

    @staticmethod
    def _print_missing(seq_nums):
        last_seq_num = 0
        for seq_num in seq_nums:
            if seq_num != last_seq_num + 1:
                print "from list im missing seq num {}".format(seq_num)
            last_seq_num = seq_num
