import struct
from enum import Enum
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import (
    ResourceContainer, SDRAMResource, IPtagResource)
from spinnman.connections.udp_packet_connections import UDPConnection
from spinnman.messages.sdp import SDPMessage, SDPHeader, SDPFlag
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities


class PacketGatherer(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0)])
    PORT = 11111

    def __init__(self):
        super(PacketGatherer, self).__init__(label="pg", constraints=None)
        self._view = None

    @property
    def resources_required(self):
        return ResourceContainer(
            sdram=SDRAMResource(constants.SYSTEM_BYTES_REQUIREMENT),
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

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=system_size,
            label='systemInfo')

    def get_binary_file_name(self):
        return "packet_gatherer.aplx"

    def get_data(self, transceiver, placement, extra_monitor_vertices,
                 placements):
        data = struct.pack("<I", 100)
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
        # set router time out
        extra_monitor_vertices[0].set_router_time_outs(
            15, 15, transceiver, placements, extra_monitor_vertices)
        transceiver.send_sdp_message(message=message)

        # receive
        output = None
        finished = False
        first = True
        offset = 0
        while not finished:
            data = connection.receive()
            length_of_data = len(data)
            if first:
                length = struct.unpack_from("<I", data, 0)[0]
                first = False
                output = bytearray(length)
                self._view = memoryview(output)
                self._view[offset:offset + length_of_data - 4] = \
                    data[4:4 + length_of_data - 4]
                offset += length_of_data - 4

            else:
                last_mc_packet = struct.unpack_from(
                    "<I", data, length_of_data - 4)[0]
                if last_mc_packet == 0xFFFFFFFF:
                    self._view[offset:offset + length_of_data - 4] = \
                        data[0:0 + length_of_data - 4]
                    offset += length_of_data - 4
                    finished = True
                else:
                    self._view[offset:offset + length_of_data] = \
                        data[0:0 + length_of_data]
                    offset += length_of_data

        # hand back
        # set router time out
        extra_monitor_vertices[0].set_router_time_outs(
            15, 4, transceiver, placements, extra_monitor_vertices)
        return output
