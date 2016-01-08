__author__ = 'gmtuca'

import struct
from result import Entry
from enum import Enum
from statement_parser import StatementParser
from statement_parser import Select
from statement_parser import InsertInto
from statement_parser import CreateTable
from result import Response

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
    """
    typedef struct Column {
        uchar    name[16];
        var_type type;
        size_t   size;
    } Column;

    typedef struct Table {
        size_t      n_cols;
        size_t      row_size;
        size_t      current_n_rows;
        Column      cols[4];
    } Table;
    """

    table = createTable.table

    maxColNameLen = 16

    total_row_size = 0
    col_name_type_size = []
    for c in table.cols:
        col_name_type_size.append((normalize(c.name, maxColNameLen), c.type, c.size))
        total_row_size += c.size

    s = struct.pack("BIIII",
                    dbCommands.CREATE_TABLE.value, id,
                    len(table.cols), total_row_size, 0)

    for col_name, col_type, col_size in col_name_type_size:
        s += struct.pack("{}c".format(maxColNameLen), *col_name)
        s += struct.pack("BI", get_datatype_enum(col_type), col_size)

    return [s]

def INSERT_INTO(id, insertInto):
    entries = list()

    for col_name, value in insertInto.columnValueMap.iteritems():
        """
        typedef struct Entry{
            uint32_t row_id;
            uchar    col_name[16];
            size_t   size;
            uchar    value[256];
        } Entry;
        """
        s = ""

        s += struct.pack("BI",
                             dbCommands.INSERT_INTO.value,
                             id) #todo...
        s += struct.pack("<I", id) #todo... CANNOT BE THE SAME
        s += struct.pack("16c", *normalize(col_name, 16))
        s += struct.pack("I{}c".format(len(value)), len(value), *value)

        entries.append(s)

    return entries

def SELECT(id, sel):
    #condition = sel.where.condition

    s = struct.pack("BI",
                    dbCommands.SELECT.value, id)

    if sel.cols is None:
        s += struct.pack("B", 0) # means wildcard *
    else:
        for c in sel.cols:
            s += struct.pack("16c", *normalize(c,16))

    """
    typedef struct selectQuery {
        spiDBcommand cmd;
        uint32_t     id;

        //uchar      table_name;
        uchar        col_names[4][16]; //If col names == 0, it means SELECT *

        //Where        where;??
        //simply do for SELECT * for now
    } selectQuery;
    """

    """

    left_value  = normalize(condition.left.value, 64)
    right_value = normalize(condition.right.value, 64)

    s += struct.pack("B64c",
                     condition.left.type.value,
                     *left_value)

    s += struct.pack("B", get_operator_value(condition.operator))

    s += struct.pack("B64c",
                     condition.right.type.value,
                     *right_value)

    """

    return [s]

def generateQueryStructs(id, queryString):
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

    #keep track of table

    """
    typedef struct Response{
        uint32_t      id;
        spiDBcommand  cmd;

        bool          success;
        uchar         x;
        uchar         y;
        uchar         p;
    } Response;
    """

    (id, cmd, success, x, y, p) = struct.unpack_from("IB?BBB", responseStr)
    cmd = get_dbCommandName(cmd)

    response = Response(id=id, cmd=cmd, success=success, x=x, y=y, p=p)

    if cmd == "SELECT":
        """
        typedef struct Entry{
            uint32_t row_id;
            uchar    col_name[16];
            size_t   size;
            uchar    value[256];
        } Entry;
        """

        data = responseStr[12:]

        row_id   = struct.unpack("I", data[:4])[0]

        col_name_with_nulls = data[4:20]
        col_name = col_name_with_nulls[:col_name_with_nulls.index('\0')]

        (size)   = struct.unpack("I", data[20:24])[0]
        value    = data[24:]

        response.data = Entry(row_id,col_name,value)

    return response
