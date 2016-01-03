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
from spinnman.model.core_subset import CoreSubset

from statement_parser import StatementParser
from statement_parser import Operand
from statement_parser import Table

import socket_translator

from result import Result

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

    CREATE_TABLE = 5
    INSERT_INTO = 6
    SELECT      = 7

class dbDataType(Enum):
    INT     = 0
    STRING  = 1

sqlTypeToEnum = {
    "int"     : dbDataType.INT.value,
    "varchar" : dbDataType.STRING.value
}

def get_datatype_enum(type):
    return sqlTypeToEnum[type]

def var_type(a):
    if type(a) is int:
        return 0
    if type(a) is str:
        return 1

    return 0

def byte_array(a):
    if type(a) is str:
        return a
    elif type(a) is int:
        return struct.pack('I', a)
    return 0

def print_bytearr(s):
    print "{}".format(":".join("{:02x}".format(ord(c)) for c in s))

def normalize(str, l):
    if type(str) is int:
        str = struct.pack('<I', str)

    if len(str) > l:
        return str[:l]

    v = [b'\0'] * l

    for i in range(len(str)):
        v[i] = str[i]

    return v

class ConditionOp(Enum):
    EQ = 0
    NE = 1
    GT = 2
    GE = 3
    LT = 4
    LE = 5
    BETWEEN = 6
    LIKE = 7
    IN = 8

opNameToEnum = {
            "="  : ConditionOp.EQ.value,
            "!=" : ConditionOp.NE.value,
            "<>" : ConditionOp.NE.value,
            ">"  : ConditionOp.GT.value,
            ">=" : ConditionOp.GE.value,
            "<"  : ConditionOp.LT.value,
            "<=" : ConditionOp.LE.value,
       "BETWEEN" : ConditionOp.BETWEEN.value,
          "LIKE" : ConditionOp.LIKE.value,
            "IN" : ConditionOp.IN.value
}

def get_operator_value(operator):
    return opNameToEnum[operator]

class sdp_packet():
    def __init__(self, bytestring):
        header = struct.unpack_from("HHIII", bytestring)

        (self.cmd_rc, self.seq, self.arg1, self.arg2, self.arg3) = header

        self.chip_x = (self.arg1 & 0x00FF0000) >> 16
        self.chip_y = (self.arg1 & 0x0000FF00) >> 8
        self.core   = (self.arg1 & 0x000000FF)

        self.success = self.arg2 != 0

        if(self.success):
            self.data_type = (self.arg2 & 0xF0000000) >> 28
            self.data_size = (self.arg2 & 0x0FFF0000) >> 16
            self.data = struct.unpack_from("{}s".format(self.data_size),
                                           bytestring,
                                           struct.calcsize("HHIII"))[0]

    def __str__(self):
        return "cmd_rc: {}, seq: {}, arg1: {}, arg2: {}, arg3: {}, data: {}"\
                .format(self.cmd_rc, self.seq, self.arg1,
                        self.arg2, self.arg3, self.data)

    def reply_data(self):
        if self.cmd_rc is dbCommands.PUT.value:
            if(self.success):
                return "{}  OK - id: {}, rtt: {}ms, chip: {}-{}, core: {}"\
                    .format(dbCommandStr(self.cmd_rc), self.seq,
                            self.arg3/1000.0, self.chip_x,
                            self.chip_y, self.core)
            else:
                return "{}  FAIL - id: {}, rtt: {}ms, chip: {}-{}, core: {}"\
                    .format(dbCommandStr(self.cmd_rc), self.seq,
                            self.arg3/1000.0, self.chip_x,
                            self.chip_y, self.core)

        elif self.cmd_rc is dbCommands.PULL.value:
            if(self.success):
                if self.data_type is dbDataType.INT.value:
                    d = "(int) {}".format(struct.unpack('I', self.data)[0])
                elif self.data_type is dbDataType.STRING.value:
                    d = "(string) {}".format(self.data)
                else:
                    d = "(byte[]) {}"\
                        .format(":".join("{:02x}".format(ord(c))
                                         for c in self.data))

                return "{} OK - id: {}, rtt: {}ms, " \
                       "chip: {}-{}, core: {}, data: {}"\
                    .format(dbCommandStr(self.cmd_rc), self.seq,
                            self.arg3/1000.0, self.chip_x,
                            self.chip_y, self.core, d)
            else:
                return "{} FAIL - id: {}, rtt: {}ms, chip: {}-{}, core: {}"\
                    .format(dbCommandStr(self.cmd_rc), self.seq,
                            self.arg3/1000.0, self.chip_x,
                            self.chip_y, self.core)
        else:
            return "FAIL - invalid return cmd_rc: {} - id: {}, " \
                   "rtt: {}ms, chip: {}-{}, core: {}"\
                .format(self.cmd_rc, self.seq,
                        self.arg3/1000.0, self.chip_x,
                        self.chip_y, self.core)

class SpiDBSocketConnection(Thread):

    def __init__(self, vertices, local_port=19999):

        self.vertices = vertices
        self.conn = UDPConnection()

        Thread.__init__(self,
                        name="spiDB_socket_connection{}"
                        .format(local_port))

        self.ip_address = "192.168.240.253" #todo should not be hardcoded
        self.port = 11111 #todo should not be hardcoded


        self.current_message_id = -1
        self.command_buffer = []
        self.sql_string = ""

        """
        self.remotehost = self._config.get("Machine", "machineName")
        self.board_version = self._config.getint("Machine", "version")

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


    def select(self, table, sel):
        self.current_message_id += 1

        condition = sel.where.condition

        s = struct.pack("BI",
                        dbCommands.SELECT.value, self.current_message_id)

        if condition.left.type == Operand.OperandType.COLUMN:
            condition.left.value = table.get_index(condition.left.value)

        if condition.right.type == Operand.OperandType.COLUMN:
            condition.right.value = table.get_index(condition.right.value)

        left_value  = normalize(condition.left.value, 64)
        print "LEFT: v {}".format(condition.left.value)
        print_bytearr(left_value)

        right_value = normalize(condition.right.value, 64)

        print "RIGHT: v {}".format(condition.right.value)
        print_bytearr(right_value)

        s += struct.pack("B64c",
                         condition.left.type.value,
                         *left_value)

        s += struct.pack("B", get_operator_value(condition.operator))

        s += struct.pack("B64c",
                         condition.right.type.value,
                         *right_value)

        print "ABOUT TO SEND:"
        print s

        self.conn.send_to(s, (self.ip_address, self.port))

        return self.current_message_id, s

    def create_table(self, table):
        self.current_message_id += 1

        """
        typedef struct Table {
            size_t      n_cols;
            size_t      row_size;
            size_t      current_n_rows;
            Column      cols[4];
        } Table;
        """

        total_row_size = 0
        col_size_type = []
        for c in table.cols:
            col_size_type.append((c.size, c.type))
            total_row_size += c.size

        s = struct.pack("BIIII",
                        dbCommands.CREATE_TABLE.value, self.current_message_id,
                        len(col_size_type), total_row_size, 0)

        for col_size, col_type in col_size_type:
            s += struct.pack("<IBBBB",
                             col_size, get_datatype_enum(col_type),
                             0, 0, 0) #these are for padding

        self.conn.send_to(s, (self.ip_address, self.port))

        return self.current_message_id, s

    def insert(self, table, field_name_to_value):
        table.current_row_id += 1

        """
        typedef struct Entry{
            uint32_t row_id;
            uint32_t col_index;
            size_t   size;
            uchar    value[256];
        } Entry;

        typedef struct insertEntryQuery { //insert into
            spiDBcommand cmd;
            uint32_t     id;

            Entry        e;
        } insertEntryQuery;
        """

        #value_colsize_ordered = [(b'\0', 0)] * len(table.cols)

        for field_name, value in field_name_to_value.iteritems():
            i, col = table.get_index_and_col(field_name)
            if i is not -1:
                #value_colsize_ordered[i] = value, col.size

                self.current_message_id += 1

                cmd_id = struct.pack("BI",
                                     dbCommands.INSERT_INTO.value,
                                     self.current_message_id)

                entry = struct.pack("III{}c".format(len(value)),
                                    table.current_row_id,
                                    i,
                                    len(value),
                                    *value)

                s = cmd_id + entry
                print "sending insert {}".format(s)

                self.conn.send_to(s, (self.ip_address, self.port))

                """
                values = ""
                for value, colsize in value_colsize_ordered:
                    value_bytearr = [b'\0'] * colsize

                    for i in range(0, len(value)):
                        value_bytearr[i] = value[i]

                    values += struct.pack("{}c".format(colsize),
                                          *value_bytearr)

                s = cmd_id + values
                """

    def put(self, k, v):
        k_str = byte_array(k)
        v_str = byte_array(v)

        self.current_message_id += 1

        k_size   = len(k_str)
        v_size   = len(v_str)
        k_v_size = k_size+v_size

        s = struct.pack("IBBIBI{}s".format(k_v_size),
                        self.current_message_id, dbCommands.PUT.value,
                        var_type(k), k_size,
                        var_type(v), v_size, "{}{}".format(k_str, v_str))

        return self.current_message_id, s

    def pull(self, k):
        k_str = byte_array(k)
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
            #time.sleep(0.001)
            self.conn.send_to(id_bytestring[1], (self.ip_address, self.port))

        for i, id_bytestring in enumerate(id_bytestrings):
            try:
                bytestring = self.conn.receive(1)
                sdp_h = sdp_packet(bytestring)
                ret[id_to_index[sdp_h.seq]] = sdp_h.reply_data()
            except:
                pass

        return ret

    def print_log(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(
                        core_subsets = [CoreSubset(x, y, [p])])
        for iobuf in iobufs:
            print iobuf

    def run(self):
        time.sleep(8) #todo should not be hardcoded

        #self.vertices[1].append(0x1234)

        self.print_log(0, 0, 1)

        self.table = None #todo

        create = """CREATE TABLE People(
        name varchar(20),
        middlename varchar(20),
        lastname varchar(20)
        );
        """
        p = StatementParser(create)
        self.table = p.CREATE_TABLE()
        self.create_table(self.table)
        print self.table

        inse = """INSERT INTO People(
        name,middlename,lastname)
        VALUES (Tuca,Bicalho,Ceccotti);
        """
        p = StatementParser(inse)
        map = p.generate_INSERT_INTO_map()
        self.insert(self.table, map)

        for i in range(10):
            inse = """INSERT INTO People(
            name,middlename,lastname)
            VALUES (Tuca{},Bicalho,Ceccotti{});
            """.format(i,i)
            p = StatementParser(inse)
            map = p.generate_INSERT_INTO_map()
            self.insert(self.table, map)

        inse = """INSERT INTO People(
            name,middlename,lastname)
            VALUES (Mincho,Pedcov,Pedcov);"""
        p = StatementParser(inse)
        map = p.generate_INSERT_INTO_map()
        self.insert(self.table, map)

        se = """SELECT *
        FROM People
        WHERE middlename = 'Bicalho';
        """

        p = StatementParser(se)
        sel = p.SELECT()
        self.select(self.table, sel)

        time_sent = time.time() * 1000

        result = Result()

        print "Let's receive!"
        while True:
            try:
                entry = socket_translator.translate(self.table, self.conn.receive(1))
                entry.response_time = time.time() * 1000 - time_sent

                print entry

                result.addEntry(entry)
            except Exception as e: #timeout TODO check for other exceptions
                print e
                break

        print result

        while True:
            try:
                cmd = raw_input("> ")

                if cmd == "":
                    pass
                elif cmd == "flush":
                    for response in self.flush(self.command_buffer):
                        print response
                    self.command_buffer = []
                elif cmd == "clear":
                    self.conn.send_to(self.clear()[1], (self.ip_address, self.port))
                    self.command_buffer = []
                elif cmd.startswith("put") or cmd.startswith("pull"):
                    self.command_buffer.append(eval("self.{}".format(cmd)))
                elif cmd == "log":
                    self.print_log(0, 0, 1)
                elif cmd.startswith("log"):
                    arr = cmd.split(" ")
                    self.print_log(int(arr[1]), int(arr[2]), int(arr[3]))
                elif cmd == "exit":
                    sys.exit(0)
                elif cmd == ".":
                    p = StatementParser(self.sql_string)

                    if p.type == "INSERT":
                        map = p.generate_INSERT_INTO_map()
                        self.insert(self.table, map)
                    elif p.type == "CREATE":
                        self.table = p.CREATE_TABLE()
                        self.create_table(self.table)
                    elif p.type == "SELECT":
                        pass

                    self.sql_string = ""
                else:
                    #self.command_buffer.append(eval(cmd))
                    self.sql_string += cmd
            except Exception:
                traceback.print_exc()