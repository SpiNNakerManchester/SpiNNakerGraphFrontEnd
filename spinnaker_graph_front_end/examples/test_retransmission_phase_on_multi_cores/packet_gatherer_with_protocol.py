import struct
import math
import time
from enum import Enum
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import (
    ConstantSDRAM, IPtagResource, ResourceContainer)
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinnman.connections.udp_packet_connections import UDPConnection
from spinnman.exceptions import SpinnmanTimeoutException
from spinnman.messages.sdp import SDPMessage, SDPHeader, SDPFlag


class PacketGathererWithProtocol(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1)])
    PORT = 11111
    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024 * 1024
    CONFIG_SIZE = 8
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

    def __init__(self):
        super(PacketGathererWithProtocol, self).__init__(
            label="pg", constraints=None)
        self._view = None
        self._max_seq_num = None
        self._output = None

    @property
    def resources_required(self):
        return ResourceContainer(
            sdram=ConstantSDRAM(
                constants.SYSTEM_BYTES_REQUIREMENT + self.CONFIG_SIZE),
            iptags=[IPtagResource(port=self.PORT, strip_sdp=True,
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
        base_key = routing_info.get_first_key_for_edge(
            list(machine_graph.get_edges_ending_at_vertex(self))[0])
        spec.write_value(base_key + 1)
        spec.write_value(base_key + 2)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=system_size,
            label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.CONFIG.value,
            size=self.CONFIG_SIZE,
            label="config")

    def get_binary_file_name(self):
        return "packet_gatherer.aplx"

    def get_data(self, transceiver, placement):

        data = struct.pack("<I", self.SDP_PACKET_START_SENDING_COMMAND_ID)
        # print("sending to core {}:{}:{}".format(
        #     placement.x, placement.y, placement.p))
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
        transceiver.set_reinjection_router_timeout(15, 15)
        transceiver.send_sdp_message(message=message)

        # receive
        finished = False
        first = True
        seq_num = 1
        seq_nums = set()
        while not finished:
            try:
                data = connection.receive(
                    timeout=self.TIMEOUT_PER_RECEIVE_IN_SECONDS)

                first, seq_num, seq_nums, finished = \
                    self._process_data(
                        data, first, seq_num, seq_nums, finished, placement,
                        transceiver)
            except SpinnmanTimeoutException:
                if not finished:
                    finished = self._transmit_missing_seq_nums(
                        seq_nums, transceiver, placement)

        # pretend that we're broken, re-require some of the data
        print("doing fake retransmission")
        missing_seq_nums = [3140, 1938]
        self._remove_seq_nums(seq_nums, missing_seq_nums)
        finished = self._transmit_missing_seq_nums(
            seq_nums, transceiver, placement)
        while not finished:
            try:
                data = connection.receive(
                    timeout=self.TIMEOUT_PER_RECEIVE_IN_SECONDS)

                first, seq_num, seq_nums, finished = \
                    self._process_data(
                        data, first, seq_num, seq_nums, finished, placement,
                        transceiver)
            except SpinnmanTimeoutException:
                if not finished:
                    finished = self._transmit_missing_seq_nums(
                        seq_nums, transceiver, placement)

        # self._check(seq_nums)
        transceiver.set_reinjection_router_timeout(15, 4)
        return self._output

    def _remove_seq_nums(self, seq_nums, missing_seq_nums):
        for seq_num in missing_seq_nums:
            seq_nums.remove(seq_num)

    def _calculate_missing_seq_nums(self, seq_nums):
        missing_seq_nums = list()
        for seq_num in range(1, self._max_seq_num):
            if seq_num not in seq_nums:
                missing_seq_nums.append(seq_num)
        return missing_seq_nums

    def _transmit_missing_seq_nums(
            self, seq_nums, transceiver, placement):
        # locate missing seq nums from pile

        missing_seq_nums = self._calculate_missing_seq_nums(seq_nums)
        if len(missing_seq_nums) == 0:
            return True

        # figure n packets given the 2 formats
        n_packets = 1
        length_via_format2 = \
            len(missing_seq_nums) - (self.DATA_PER_FULL_PACKET - 2)
        if length_via_format2 > 0:
            n_packets += int(math.ceil(
                float(length_via_format2) /
                float(self.DATA_PER_FULL_PACKET - 1)))

        # transmit missing seq as a new sdp packet
        first = True
        seq_num_offset = 0
        for _packet_count in range(0, n_packets):
            length_left_in_packet = self.DATA_PER_FULL_PACKET
            offset = 0
            data = None
            size_of_data_left_to_transmit = None

            # if first, add n packets to list
            if first:

                # get left over space / data size
                size_of_data_left_to_transmit = min(
                    length_left_in_packet - 2,
                    len(missing_seq_nums) - seq_num_offset)

                # build data holder accordingly
                data = bytearray(
                    (size_of_data_left_to_transmit + 2) *
                    self.WORD_TO_BYTE_CONVERTER)

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

            else:  # just add data
                # get left over space / data size
                size_of_data_left_to_transmit = min(
                    self.DATA_PER_FULL_PACKET_WITH_SEQUENCE_NUM,
                    len(missing_seq_nums) - seq_num_offset)

                # build data holder accordingly
                data = bytearray(
                    (size_of_data_left_to_transmit + 1) *
                    self.WORD_TO_BYTE_CONVERTER)

                # pack flag
                struct.pack_into(
                    "<I", data, offset,
                    self.SDP_PACKET_MISSING_SEQ_COMMAND_ID)
                offset += 1 * self.WORD_TO_BYTE_CONVERTER
                length_left_in_packet -= 1

            # fill data field
            struct.pack_into(
                "<{}I".format(size_of_data_left_to_transmit), data, offset,
                *missing_seq_nums[
                 seq_num_offset:
                 seq_num_offset + size_of_data_left_to_transmit])
            seq_num_offset += length_left_in_packet

            # build sdp message
            message = SDPMessage(
                sdp_header=SDPHeader(
                    destination_chip_x=placement.x,
                    destination_chip_y=placement.y,
                    destination_cpu=placement.p,
                    destination_port=self.SDP_PACKET_PORT,
                    flags=SDPFlag.REPLY_NOT_EXPECTED),
                data=data)

            # debug
            self._print_out_packet_data(data)

            # send message to core
            transceiver.send_sdp_message(message=message)

            # sleep for ensuring core doesnt lose packets
            time.sleep(self.TIME_OUT_FOR_SENDING_IN_SECONDS)
            # self._print_packet_num_being_sent(packet_count, n_packets)
        return False

    def _process_data(self, data, first, seq_num, seq_nums, finished,
                      placement, transceiver):
        # self._print_out_packet_data(data)
        length_of_data = len(data)
        if first:
            length = struct.unpack_from("<I", data, 0)[0]
            first = False
            self._output = bytearray(length)
            self._view = memoryview(self._output)
            self._write_into_view(
                0, length_of_data - self.LENGTH_OF_DATA_SIZE,
                data,
                self.LENGTH_OF_DATA_SIZE, length_of_data, seq_num,
                length_of_data, False)

            # deduce max seq num for future use
            self._max_seq_num = self.calculate_max_seq_num()

        else:  # some data packet
            first_packet_element = struct.unpack_from(
                "<I", data, 0)[0]
            last_mc_packet = struct.unpack_from(
                "<I", data, length_of_data - self.END_FLAG_SIZE)[0]

            # if received a last flag on its own, its during retransmission.
            #  check and try again if required
            if (last_mc_packet == self.END_FLAG and
                    length_of_data == self.END_FLAG_SIZE):
                if not self._check(seq_nums):
                    finished = self._transmit_missing_seq_nums(
                        placement=placement, transceiver=transceiver,
                        seq_nums=seq_nums)
            else:
                # this flag can be dropped at some point
                seq_num = first_packet_element
                # print("seq num = {}".format(seq_num))
                if seq_num > self._max_seq_num:
                    raise Exception(
                        "got an insane sequence number. got {} when "
                        "the max is {} with a length of {}".format(
                            seq_num, self._max_seq_num, length_of_data))
                seq_nums.add(seq_num)

                # figure offset for where data is to be put
                offset = self._calculate_offset(seq_num)

                # write excess data as required
                if last_mc_packet == self.END_FLAG:

                    # adjust for end flag
                    true_data_length = (
                        length_of_data - self.END_FLAG_SIZE -
                        self.SEQUENCE_NUMBER_SIZE)

                    # write data
                    self._write_into_view(
                        offset, offset + true_data_length,
                        data, self.SEQUENCE_NUMBER_SIZE,
                        length_of_data - self.END_FLAG_SIZE, seq_num,
                        length_of_data, True)

                    # check if need to retry
                    if not self._check(seq_nums):
                        finished = self._transmit_missing_seq_nums(
                            placement=placement, transceiver=transceiver,
                            seq_nums=seq_nums)
                    else:
                        finished = True

                else:  # full block of data, just write it in
                    true_data_length = (
                        offset + length_of_data - self.SEQUENCE_NUMBER_SIZE)
                    self._write_into_view(
                        offset, true_data_length, data,
                        self.SEQUENCE_NUMBER_SIZE,
                        length_of_data, seq_num, length_of_data, False)
        return first, seq_num, seq_nums, finished

    def _calculate_offset(self, seq_num):
        offset = (seq_num * self.DATA_PER_FULL_PACKET_WITH_SEQUENCE_NUM *
                  self.WORD_TO_BYTE_CONVERTER)
        return offset

    def _write_into_view(
            self, view_start_position, view_end_position,
            data, data_start_position, data_end_position, seq_num,
            packet_length, is_final):
        """ puts data into the view

        :param view_start_position: where in view to start
        :param view_end_position: where in view to end
        :param data: the data holder to write from
        :param data_start_position: where in data holder to start from
        :param data_end_position: where in data holder to end
        :param seq_num: the seq number to figure
        :rtype: None
        """
        if view_end_position > len(self._output):
            raise Exception(
                "I'm trying to add to my output data, but am trying to add "
                "outside my acceptable output positions!!!! max is {} and "
                "I received request to fill to {} for seq num {} from max "
                "seq num {} length of packet {} and final {}".format(
                    len(self._output), view_end_position, seq_num,
                    self._max_seq_num, packet_length, is_final))
        # print("view_start={} view_end={} data_start={} data_end={}".format(
        #     view_start_position, view_end_position, data_start_position,
        #     data_end_position))
        self._view[view_start_position: view_end_position] = \
            data[data_start_position:data_end_position]

    def _check(self, seq_nums):
        # hand back
        seq_nums = sorted(seq_nums)
        max_needed = self.calculate_max_seq_num()
        if len(seq_nums) > max_needed:
            raise Exception("I've received more data than i was expecting!!")
        if len(seq_nums) != max_needed:
            # self._print_length_of_received_seq_nums(seq_nums, max_needed)
            return False
        return True

    def calculate_max_seq_num(self):
        n_sequence_numbers = 0
        data_left = len(self._output) - (
            (self.DATA_PER_FULL_PACKET -
             self.SDP_RETRANSMISSION_HEADER_SIZE) *
            self.WORD_TO_BYTE_CONVERTER)

        extra_n_sequences = float(data_left) / float(
            self.DATA_PER_FULL_PACKET_WITH_SEQUENCE_NUM *
            self.WORD_TO_BYTE_CONVERTER)
        n_sequence_numbers += math.ceil(extra_n_sequences)
        return int(n_sequence_numbers)

    @staticmethod
    def _print_missing(seq_nums):
        last_seq_num = 0
        seq_nums = sorted(seq_nums)
        for seq_num in seq_nums:
            if seq_num != last_seq_num + 1:
                print("from list im missing seq num {}".format(seq_num))
            last_seq_num = seq_num

    def _print_out_packet_data(self, data):
        reread_data = struct.unpack("<{}I".format(
            int(math.ceil(len(data) / self.WORD_TO_BYTE_CONVERTER))),
            data)
        print("converted data back into readable form is {}".format(
            reread_data))

    @staticmethod
    def _print_length_of_received_seq_nums(seq_nums, max_needed):
        if len(seq_nums) != max_needed:
            print("should have received {} sequence numbers, but received "
                  "{} sequence numbers".format(max_needed, len(seq_nums)))
            return False

    @staticmethod
    def _print_packet_num_being_sent(packet_count, n_packets):
        print("send sdp packet with missing seq nums: {} of {}".format(
            packet_count + 1, n_packets))
