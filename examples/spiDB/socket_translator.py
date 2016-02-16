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


sqlTypeToEnum = {
    "int"     : 0,
    "varchar" : 1
}

def get_datatype_enum(type):
    return sqlTypeToEnum[type]

def get_operator_value(operator):
    return opNameToEnum[operator]

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
        s += struct.pack("{}c".format(maxColNameLen), *col_name)
        s += struct.pack("BI", get_datatype_enum(col_type), col_size)

    return [s]

def INSERT_INTO(id, insertInto):
    entries = list()

    for col_name, value in insertInto.columnValueMap.iteritems():
        entries.append(
             struct.pack("BI", dbCommands.INSERT_INTO.value, id) +\
             struct.pack("16c", *normalize(insertInto.tableName, 16)) +\
             struct.pack("<I", id) +\
             struct.pack("16c", *normalize(col_name, 16)) +\
             struct.pack("I{}c".format(len(value)), len(value), *value)
        )

    return entries

def PING(id):
    return struct.pack("BI",dbCommands.PING.value, id)

def SELECT(id, sel):
    #condition = sel.where.condition

    s = struct.pack("BI", dbCommands.SELECT.value, id)

    if sel.cols is None:
        s += struct.pack("B", 0) # means wildcard *
    else:
        for c in sel.cols:
            s += struct.pack("16c", *normalize(c,16))
        s += struct.pack("B", 0) #so that we set the next col to null for scan.h

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
        r"\s+((?:\"|\')?.+(?:\"|\'))?\s+((?:\"|\')?.+(?:\"|\')?)\s*")

pull_pattern = re.compile(
    r"\s*(?:PULL|pull|POP|pop)"
        r"\s+((?:\"|\')?.+(?:\"|\'))?\s*")

def convertFromUnicode(u):
    s = u.encode('ascii','ignore')

    if      s.isdigit(): return int(s)
    elif    s.startswith("\"") or s.startswith("\'"): return s[1:-1]
    else:   return s

def generateQueryStructs(id, queryString):
    if queryString is None:
        return None

    upper = queryString.upper()
    if upper.startswith("PUT") or upper.startswith("PUSH"):
        m = put_pattern.match(queryString)
        if m is None:
            raise Exception("Invalid PUT format")

        print m.groups()
        k = convertFromUnicode(m.group(1))
        v = convertFromUnicode(m.group(2))
        return PUT(id, k, v)

    if upper.startswith("PULL") or upper.startswith("POP"):
        m = pull_pattern.match(queryString)
        if m is None:
            raise Exception("Invalid PULL format")

        print m.groups()
        k = convertFromUnicode(m.group(1))
        return PULL(id, k)


    p = StatementParser(queryString)
    inst = p.parse()

    if isinstance(inst, CreateTable):
        return CREATE_TABLE(id, inst)
    elif isinstance(inst, InsertInto):
        return INSERT_INTO(id, inst)
    elif isinstance(inst, Select):
        return SELECT(id, inst)
    else:
        return None

def translateResponse(responseStr):
    (id, cmd, success, x, y, p) = struct.unpack_from("IB?BBB", responseStr)
    cmd = get_dbCommandName(cmd)

    response = Response(id=id, cmd=cmd, success=success, x=x, y=y, p=p)

    if cmd == "SELECT":
        data = responseStr[12:]

        row_id   = struct.unpack("I", data[:4])[0]

        col_name_with_nulls = data[4:20]
        col_name = col_name_with_nulls[:col_name_with_nulls.index('\0')]

        (size)   = struct.unpack("I", data[20:24])[0]
        value    = data[24:]

        response.data = Entry(row_id,col_name,value)
    elif cmd == "INSERT_INTO":
        response.data = responseStr[12:]
        i = response.data.index('\0')
        if i > 0:
            response.data = response.data[:i]

    return response