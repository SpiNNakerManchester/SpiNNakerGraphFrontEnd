__author__ = 'gmtuca'

import struct
from result import Entry
from enum import Enum
from statement_parser import StatementParser
from statement_parser import Select
from statement_parser import InsertInto
from statement_parser import CreateTable
from result import Response
import re

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

class dbCommands(Enum):
    PUT   = 0
    PULL  = 1
    CLEAR = 2

    CREATE_TABLE = 5
    INSERT_INTO = 6
    SELECT      = 7

    PING = 9

dbCommandIntToName = {
    dbCommands.PUT.value :          "PUT",
    dbCommands.PULL.value :         "PULL",
    dbCommands.CREATE_TABLE.value : "CREATE_TABLE",
    dbCommands.INSERT_INTO.value :  "INSERT_INTO",
    dbCommands.SELECT.value :       "SELECT"
}

def get_dbCommandName(n):
    return dbCommandIntToName[n]

def get_datatype_enum(type):
    if type == 'integer':
        return 0
    if type == 'varchar':
        return 1
    return -1

def get_datatype_name(type):
    if type == 0:
        return 'integer'
    if type == 1:
        return 'varchar'
    return None

def get_operator_value(operator):
    return opNameToEnum[operator]

def print_bytearr(s):
    print "{}".format(":".join("{:02x}".format(ord(c)) for c in s))

def normalize(s, l=0):
    if type(s) is int:
        s = struct.pack('<I', s)
        if l is 0:
            return s
        else:
            return normalize(s, l)

    if l is 0:
        raise Exception("Normalization with l=0")

    if len(s) > l:
        return s[:l]

    v = [b'\0'] * l

    for i in range(len(s)):
        v[i] = s[i]

    return v

def CREATE_TABLE(id, createTable):
    table = createTable.table

    maxColNameLen = 16

    total_row_size = 0
    col_name_type_size = []
    for c in table.cols:
        col_name_type_size.append((normalize(c.name, maxColNameLen), c.type, c.size))
        total_row_size += c.size

    s = struct.pack("BI", dbCommands.CREATE_TABLE.value, id) +\
        struct.pack("16c", *normalize(table.name, 16)) +\
        struct.pack("III", len(table.cols), total_row_size, 0)

    for col_name, col_type, col_size in col_name_type_size:
        s += struct.pack("{}c".format(maxColNameLen), *col_name) +\
             struct.pack("BI", get_datatype_enum(col_type), col_size)

    return [s]

def INSERT_INTO(id, insertInto):
    entries = list()

    for col_name, value in insertInto.columnValueMap.iteritems():
        e_size = len(value) if type(value) is str else 4

        entries.append(
             struct.pack("BI", dbCommands.INSERT_INTO.value, id) +
             struct.pack("16c", *normalize(insertInto.tableName, 16)) +
             struct.pack("<I", id) +
             struct.pack("16c", *normalize(col_name, 16)) +
             struct.pack("IB{}c".format(e_size),
                         e_size,
                         get_datatype_enum('integer') if type(value) is int
                            else get_datatype_enum('varchar'),
                         *normalize(value, e_size if type(value) is str else 0))
        )

    return entries

def PING(id):
    return struct.pack("BI",dbCommands.PING.value, id)

def SELECT(id, sel):
    s = struct.pack("BI", dbCommands.SELECT.value, id) +\
        struct.pack("16c", *normalize(sel.tableName, 16))

    for i in range(6): #max number of cols
        if sel.cols is not None and i < len(sel.cols):
            s += struct.pack("16c", *normalize(sel.cols[i], 16))
        else:
            #wildcard *
            s += struct.pack("16c", *normalize('', 16))

    if sel.where is None:
        # no WHERE clause
        s += struct.pack("BB", 0, 0)
    else:
        condition = sel.where.condition
        l = condition.left
        r = condition.right

        s += struct.pack("B64c", l.type.value, *normalize(l.value, 64)) +\
             struct.pack("B", get_operator_value(condition.operator)) +\
             struct.pack("B64c", r.type.value, *normalize(r.value, 64))

    return [s]

def byte_array(a):
    if type(a) is str:
        return a
    elif type(a) is int:
        return struct.pack('I', a)
    return 0

def var_type(a):
    if type(a) is int:
        return 0
    if type(a) is str:
        return 1
    return 0

def PUT(id, k, v):
    k_str = byte_array(k)
    v_str = byte_array(v)

    k_size = len(k_str)
    v_size = len(v_str)

    info = (var_type(k) << 28) | (k_size << 16) |\
           (var_type(v) << 12) | (v_size)

    s = struct.pack("BII{}s".format(k_size+v_size),
                    dbCommands.PUT.value, id, info,
                    "{}{}".format(k_str, v_str))
    return [s]

def PULL(id, k):
    k_str = byte_array(k)
    k_size = len(k_str)

    info = (var_type(k) << 28) | (k_size << 16)

    s = struct.pack("BII{}s".format(k_size),
                    dbCommands.PULL.value, id, info, k_str)
    return [s]

put_pattern = re.compile(
    r"\s*(?:PUT|put|PUSH|push)"
        r"\s+((?:\"|\')?.+(?:\"|\')?)\s+((?:\"|\')?.+(?:\"|\')?)\s*")

pull_pattern = re.compile(
    r"\s*(?:PULL|pull|POP|pop)"
        r"\s+((?:\"|\')?.+(?:\"|\')?)\s*")


def convertFromUnicode(u):
    s = u.encode('ascii','ignore')
    if s.isdigit():
        return int(s)
    elif s[0] in ('"', '\'') and s[-1] == s[0]:
        return s[1:-1]
    else:
        return s

def generateQueryStructs(id, queryString, type="SQL"):
    if queryString is None:
        return None

    if type == "SQL":
        inst = StatementParser.parse(queryString)
        print inst

        if isinstance(inst, CreateTable):
            return CREATE_TABLE(id, inst)
        elif isinstance(inst, InsertInto):
            return INSERT_INTO(id, inst)
        elif isinstance(inst, Select):
            return SELECT(id, inst)
        else:
            return None
    else:
        upper = queryString.upper()
        if upper.startswith("PUT") or upper.startswith("PUSH"):
            m = put_pattern.match(queryString)
            if m is None:
                raise Exception("Invalid PUT format")

            k = convertFromUnicode(m.group(1))
            v = convertFromUnicode(m.group(2))
            return PUT(id, k, v)

        if upper.startswith("PULL") or upper.startswith("POP"):
            m = pull_pattern.match(queryString)
            if m is None:
                raise Exception("Invalid PULL format")

            k = convertFromUnicode(m.group(1))
            return PULL(id, k)

def translateResponse(responseStr):

    (id, cmd, success, x, y, p) = struct.unpack_from("IB?BBB", responseStr)
    cmd = get_dbCommandName(cmd)

    response = Response(id=id, cmd=cmd, success=success, x=x, y=y, p=p)

    if cmd == "SELECT":
        data = responseStr[9:]

        row_id   = struct.unpack("I", data[:4])[0]

        col_name_with_nulls = data[4:20]
        col_name = col_name_with_nulls[:col_name_with_nulls.index('\0')]

        (size)   = struct.unpack("I", data[20:24])[0]
        type     = get_datatype_name(struct.unpack("B", data[24:25])[0])
        value    = data[25:]

        if(type == 'integer'):
            value = struct.unpack("<I", value)[0]

        response.data = Entry(row_id=row_id, type=type, size=size,
                              col=col_name, value=value)
    elif cmd == "INSERT_INTO":
        response.data = responseStr[9:]
        i = response.data.index('\0')
        if i > 0:
            response.data = response.data[:i]
    elif cmd == "PULL":
        response.data = responseStr[9:]

    return response