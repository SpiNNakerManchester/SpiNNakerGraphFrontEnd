__author__ = 'Arthur'

from enum import Enum
import re

class Operand:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def __str__(self):
        return "{} ({})".format(self.value, self.type)

    class OperandType(Enum):
        LITERAL_UINT32  = 0
        LITERAL_STRING  = 1
        COLUMN          = 2

class Condition:
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __str__(self):
        return "{} {} {}".format(self.left, self.operator, self.right)

class Select:
    def __init__(self, tableName, cols=None, where=None):
        self.tableName = tableName
        self.cols = cols # None means '*'
        self.where = where

    def __str__(self):
        return "SELECT {} FROM {}{};"\
            .format('*' if self.cols is None else self.cols,
                    self.tableName,
                    " WHERE {}".format(str(self.where)) if self.where else "")

    def __repr__(self):
        return self.__str__()

class InsertInto:
    def __init__(self, tableName, columnValueMap):
        self.tableName = tableName
        self.columnValueMap = columnValueMap

    def __str__(self):
        return "INSERT INTO {}({}) VALUES ({});"\
                    .format(self.tableName, self.columnValueMap.keys(),
                            self.columnValueMap.values())

class Where:
    def __init__(self, condition):
        self.condition = condition

    def __str__(self):
        return str(self.condition)

class Column:
    def __init__(self, name, type, size):
        self.name = name
        self.type = type
        self.size = size

    def __str__(self):
        return "{} {}({})"\
                .format(self.name, self.type, self.size)

    def __repr__(self):
       return self.__str__()

class CreateTable():
    def __init__(self,table):
        self.table = table

    def __str__(self):
        return "CREATE TABLE {}".format(self.table)

class Table:
    def __init__(self, name, cols):
        self.name = name
        self.cols = cols

    def __str__(self):
        return "{}({})".format(self.name, self.cols)

    def get_index(self, col_name):
        for i in range(len(self.cols)):
            if self.cols[i].name == col_name:
                return i
        return -1

    def get_size(self, col_name):
        for c in self.cols:
            if c.name == col_name:
                return c.size
        return 0

    def get_index_and_col(self, col_name):
        for i in range(len(self.cols)):
            if self.cols[i].name == col_name:
                return i, self.cols[i]
        return -1, None

class InvalidQueryException(Exception):
    pass

class StatementParser:

    select_pattern = \
        re.compile( r"^SELECT\s+(\*|(?:\w+\s*,?\s*)+)\s*"
                    r"FROM\s+(\w+)(?:\s+"
                    r"WHERE\s+((?:[\"\']?\w+[\"\']?)|\d+)\s*"
                        r"(\=|\!\=|<>|>|>\=|<|\<=|BETWEEN|LIKE|IN)"
                        r"\s*((?:[\"\']?\w+[\"\']?)|\d+))?\s*;?\s*$")

    insert_pattern = \
        re.compile( r"^INSERT\s+INTO\s+(\w+)\s*"
                    r"\(\s*((?:\w+\s*,?\s*)+)\)\s+"
                    r"VALUES\s*"
                        r"\(\s*((?:(?:[\"\']\w+[\"\']|\d+)\s*,?\s*)+)\)\s*;?\s*$")

    create_pattern = \
        re.compile(
            r"^CREATE\s+TABLE\s+(\w+)\s*"
            r"\(((?:\s*\w+\s+(?:varchar\s*\(\s*\d+\s*\)|integer)\s*,?)+)\s*\)\s*;?\s*$")


    varchar_size_pattern = re.compile(r"^varchar\s*\(\s*(\d+)\s*\)$")

    @staticmethod
    def CREATE(sql_string):
        m = StatementParser.create_pattern.match(sql_string)
        if m is None:
            raise InvalidQueryException("Invalid CREATE TABLE format")

        tableName = m.group(1)

        cols = []

        params = m.group(2).split(',')
        for p in params:
            (name, type) = re.sub('\s+', ' ', p.strip()).split(' ')
            if type == 'integer':
                size = 4
            else:
                s_m = StatementParser.varchar_size_pattern.match(type)
                type = 'varchar'
                size = int(s_m.group(1))

            cols.append(Column(name=str(name), type=str(type), size=size))

        table = Table(name=str(tableName),cols=cols)

        return CreateTable(table)

    @staticmethod
    def INSERT(sql_string):
        m = StatementParser.insert_pattern.match(sql_string)
        if m is None:
            raise InvalidQueryException("Invalid INSERT INTO format")

        tableName = m.group(1)

        fields = m.group(2)

        cols = [str(c.strip()) for c in fields.split(',')]

        values = []

        for v in m.group(3).split(','):
            v = v.strip()
            if v.isdigit():
                values.append(int(v))
            elif v[0] in ('"', '\'') and v[-1] == v[0]:
                values.append(str(v[1:-1]))
            else:
                values.append(str(v))

        map = {}
        for i in range(len(cols)):
            map[cols[i]] = values[i]

        return InsertInto(tableName=str(tableName), columnValueMap=map)

    @staticmethod
    def SELECT(sql_string):
        m = StatementParser.select_pattern.match(sql_string)
        if m is None:
            raise InvalidQueryException("Invalid SELECT format")

        fields = m.group(1)

        cols = None if fields == '*'\
            else [str(c.strip()) for c in fields.split(',')]

        tableName = m.group(2)

        if m.lastindex == 2:
            where = None
        else:
            left = StatementParser.get_operand(m.group(3))
            operator = str(m.group(4))
            right = StatementParser.get_operand(m.group(5))

            where = Where(Condition(left=left, operator=operator, right=right))

        return Select(tableName=str(tableName), cols=cols, where=where)

    @staticmethod
    def parse(sql_string):
        if sql_string.startswith("INSERT"):
            return StatementParser.INSERT(sql_string)
        if sql_string.startswith("SELECT"):
            return StatementParser.SELECT(sql_string)
        if sql_string.startswith("CREATE"):
            return StatementParser.CREATE(sql_string)
        raise InvalidQueryException("Invalid/unsupported SQL format")

    @staticmethod
    def get_operand(s):
        if s[0] in ('"', '\'') and s[-1] == s[0]:
            return Operand(Operand.OperandType.LITERAL_STRING, str(s[1:-1]))
        if s.isdigit():
            return Operand(Operand.OperandType.LITERAL_UINT32, int(s))
        return Operand(Operand.OperandType.COLUMN, str(s))