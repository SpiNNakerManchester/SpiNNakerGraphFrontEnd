from spinnman.connections.udp_packet_connections.udp_connection \
    import UDPConnection

from threading import Thread
import traceback
import logging

import time
import struct

import sys

from enum import Enum
from spinnman.transceiver import create_transceiver_from_hostname
from spinnman.model.core_subsets import CoreSubsets
from spinnman.model.core_subset import CoreSubset

logger = logging.getLogger(__name__)

def dbCommandStr(value):
    if(value is 0):
        return "PUT"
    if(value is 1):
        return "PULL"
    return "?"

class dbCommands(Enum):
    PUT   = 0
    PULL  = 1
    CLEAR = 2

class dbDataType(Enum):
    INT     = 0
    STRING  = 1

def var_type(a):
    if type(a) is int:
        return 0
    if type(a) is str:
        return 1

    return 0

def bytearray(a):
    if type(a) is str:
        return a
    elif type(a) is int:
        return struct.pack('I', a)

    return 0

class sdp_packet():
    def __init__(self, bytestring):
        header = struct.unpack_from("HHIII", bytestring)

        (self.cmd_rc, self.seq, self.arg1, self.arg2, self.arg3) = header

        self.chip_x = (self.arg1 & 0x00FF0000) >> 16
        self.chip_y = (self.arg1 & 0x0000FF00) >> 8
        self.core   = (self.arg1 & 0x000000FF)

        self.data_type = (self.arg2 & 0xF0000000) >> 28
        self.data_size = (self.arg2 & 0x0FFF0000) >> 16

        #arg2 represents info. least significant 12 bits are the size
        self.data = struct.unpack_from("{}s".format(self.data_size), bytestring, struct.calcsize("HHIII"))[0]

    def __str__(self):
        return "cmd_rc: {}, seq: {}, arg1: {}, arg2: {}, arg3: {}, data: {}"\
                .format(self.cmd_rc, self.seq, self.arg1, self.arg2, self.arg3, self.data)

    def reply_data(self):
        if self.core is 255:
            return "FAIL - id: {}, rtt: {}"\
                .format(self.seq, self.arg3)

        if self.cmd_rc is dbCommands.PUT.value:
            return "{}: OK - id: {}, rtt: {}ms, chip: {}-{}, core: {}"\
                .format(dbCommandStr(self.cmd_rc), self.seq, self.arg3/1000.0, self.chip_x, self.chip_y, self.core)
        elif self.cmd_rc is dbCommands.PULL.value:
            if self.data_type is dbDataType.INT.value:
                d = "(int) {}".format(struct.unpack('I', self.data)[0])
            elif self.data_type is dbDataType.STRING.value:
                d = "(string) {}".format(self.data)
            else:
                d = "(byte[]) {}".format(":".join("{:02x}".format(ord(c)) for c in self.data))

            return "{} OK - id: {}, rtt: {}ms, chip: {}-{}, core: {}, data: {}"\
                .format(dbCommandStr(self.cmd_rc), self.seq, self.arg3/1000.0, self.chip_x, self.chip_y, self.core, d)
        else:
            return "FAIL - invalid return cmd_rc: {} - id: {}, rtt: {}ms, chip: {}-{}, core: {}"\
                .format(self.cmd_rc, self.seq, self.arg3/1000.0, self.chip_x, self.chip_y, self.core)

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

        self.conn = UDPConnection()

        Thread.__init__(self,
                        name="spiDB_socket_connection{}"
                        .format(local_port))

        self.ip_address = "192.168.240.253" #todo should not be hardcoded
        self.port = 11111
        self.start()

        self.current_message_id = -1
        self.command_buffer = []

        #self.remotehost = self._config.get("Machine", "machineName")
        #self.board_version = self._config.getint("Machine", "version")
        """
        self.bmp_names = self._config.get("Machine", "bmp_names")
        if self.bmp_names == "None":
            self.bmp_names = None
        self.auto_detect_bmp = \
            self._config.getboolean("Machine", "auto_detect_bmp")
        self.localport = 54321
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((self.remotehost, 0))
        self.localhost = s.getsockname()[0]
        """

        self.transceiver = create_transceiver_from_hostname(self.ip_address, 3)

    def clear(self):
        self.current_message_id += 1

        s = struct.pack("IB", self.current_message_id, dbCommands.CLEAR.value)

        return self.current_message_id, s

    def put(self, k, v):
        k_str = bytearray(k)
        v_str = bytearray(v)

        self.current_message_id += 1

        k_size   = len(k_str)
        v_size   = len(v_str)
        k_v_size = k_size+v_size

        #root
        #cluster head
        #cluster slaves

        s = struct.pack("IBBIBI{}s".format(k_v_size),
                        self.current_message_id, dbCommands.PUT.value,
                        var_type(k), k_size,
                        var_type(v), v_size, "{}{}".format(k_str, v_str))

        #print ":".join("{:02x}".format(ord(c)) for c in s)

        return self.current_message_id, s

    def pull(self, k):
        k_str = bytearray(k)
        self.current_message_id += 1

        k_size   = len(k_str)

        s = struct.pack("IBBIBI{}s".format(k_size),
                        self.current_message_id, dbCommands.PULL.value,
                        var_type(k), k_size,
                        0, 0,
                        k_str)

        return self.current_message_id, s

    def flush(self, id_bytestrings):

        id_to_index = {}

        ret = [None] * len(id_bytestrings)

        for i, id_bytestring in enumerate(id_bytestrings):
            id_to_index[id_bytestring[0]] = i
            time.sleep(0.001)
            self.conn.send_to(id_bytestring[1], (self.ip_address, self.port))

        for i, id_bytestring in enumerate(id_bytestrings):
            try:
                bytestring = self.conn.receive(1)
                #print ":".join("{:02x}".format(ord(c)) for c in bytestring)
                sdp_h = sdp_packet(bytestring)
                #print "sdp_packet : {}".format(sdp_h)
                ret[id_to_index[sdp_h.seq]] = sdp_h.reply_data()
            except:
                pass

        return ret

    def print_log(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(core_subsets = [CoreSubset(x, y, [p])])
        for iobuf in iobufs:
            print iobuf

    def run(self):
        time.sleep(9) #todo change!!!!

        self.print_log(0, 0, 1)

        while True:
            try:
                cmd = raw_input("> ")

                if cmd == "flush":
                    print self.flush(self.command_buffer)
                    self.command_buffer = []
                elif cmd == "clear":
                    self.conn.send_to(self.clear()[1], (self.ip_address, self.port))
                    self.command_buffer = []
                elif cmd.startswith("put") or cmd.startswith("pull"):
                    self.command_buffer.append(eval("self.{}".format(cmd)))
                elif cmd.startswith("log"):
                    arr = cmd.split(" ")
                    self.print_log(int(arr[1]), int(arr[2]), int(arr[3]))
                elif cmd == "exit":
                    sys.exit(0)
                else:
                    self.command_buffer.append(eval(cmd))

            except Exception:
                traceback.print_exc()
                time.sleep(1)