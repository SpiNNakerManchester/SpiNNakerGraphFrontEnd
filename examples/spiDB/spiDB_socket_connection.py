from spinnman.connections.udp_packet_connections.udp_connection \
    import UDPConnection

from threading import Thread
import traceback
import logging

import time
import struct

from enum import Enum

logger = logging.getLogger(__name__)

class dbCommands(Enum):
    PUT  = 0
    PULL = 1

def var_type(a):
    if type(a) is str:
        return 2

    return 0

def bytearray(a):
    if type(a) is str:
        return a
    elif type(a) is int:
        return struct.pack('I', a)[0]

class sdp_packet():
    def __init__(self, bytestring):
        header = struct.unpack_from("HHIII", bytestring)

        (self.cmd_rc, self.seq, self.arg1, self.arg2, self.arg3) = header

        #arg2 represents info. first 12 bits are the size
        self.data = struct.unpack_from("{}s".format(self.arg2 & 0xFFF), bytestring, struct.calcsize("HHIII"))[0]

    def __str__(self):
        return "cmd_rc: {}, seq: {}, arg1: {}, arg2: {}, arg3: {}, data: {}"\
                .format(self.cmd_rc, self.seq, self.arg1, self.arg2, self.arg3, self.data)

    def reply_data(self):
        chip = self.arg1 & 0xFF00 >> 16
        core = self.arg1 & 0x00FF

        if core is 255:
            return "FAIL - (id: {}, rtt: {})"\
                .format(self.seq, self.arg3)

        if self.cmd_rc is dbCommands.PUT.value:
            return "OK - (id: {}, rtt: {}, chip: {}, core: {})"\
                .format(self.seq, self.arg3, chip, core)
        else:
            return "OK - (id: {}, rtt: {}, chip: {}, core: {}, data: {})"\
                .format(self.seq, self.arg3, chip, core, self.data)

class SpiDBSocketConnection(Thread):
    """ A connection from the toolchain which will be notified\
        when the database has been written, and can then respond when the\
        database has been read, and further wait for notification that the\
        simulation has started.
    """

    def __init__(self, local_port=19999):
        """

        :param start_callback_function: A function to be called when the start\
                    message has been received.  This function should not take\
                    any parameters or return anything.
        :type start_callback_function: function() -> None
        :param local_host: Optional specification of the local hostname or\
                    ip address of the interface to listen on
        :type local_host: str
        :param local_port: Optional specification of the local port to listen\
                    on.  Must match the port that the toolchain will send the\
                    notification on (19999 by default)
        :type local_port: int
        """

        #self._sender_connection = UDPEIEIOConnection()

        self.conn = UDPConnection()

        Thread.__init__(self,
                        name="spynnaker database connection for {}"
                        .format(local_port))

        self.ip_address = "192.168.240.253" #todo should not be hardcoded
        self.port = 11111
        self.start()

    def put(self, k, v):
        k_str = bytearray(k)
        v_str = bytearray(v)

        s = struct.pack("BBI128sBI128s", dbCommands.PUT.value,
                        var_type(k), len(k_str), k_str,
                        var_type(v), len(v_str), v_str)

        self.conn.send_to(s, (self.ip_address, self.port))

    def pull(self, k):
        k_str = bytearray(k)

        s = struct.pack("BBI128sBI128s", dbCommands.PULL.value,
                        var_type(k), len(k_str), k_str,
                        0, 0, "")

        self.conn.send_to(s, (self.ip_address, self.port))

    def run(self):
        time.sleep(8) #todo hmmmmmmmmmm

        while True:
            try:
                cmd = raw_input("> ")
                if cmd is "exit":
                    break;

                exec(cmd)

                bytestring = self.conn.receive()
                sdp_h = sdp_packet(bytestring)
                print sdp_h.reply_data()
            except Exception:
                traceback.print_exc()
                time.sleep(1)