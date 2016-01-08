__author__ = 'gmtuca'

import sqlparse
from sqlparse import sql
from sqlparse import tokens as T
from enum import Enum

class Operand:
    def __init__(self, type, value):
        self.type = type
        self.value = str(value)

    def __str__(self):
        return "{} ({})".format(self.value, self.type)

    class OperandType(Enum):
        COLUMN   = 0
        LITERAL  = 1

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
        if cols is None:
            self.wildcard = True
        else:
            self.wildcard = False

        self.cols = cols # None means '*'
        self.where = where

    def __str__(self):
        return "SELECT {} FROM {} WHERE {}"\
            .format('*' if self.cols is None else self.cols,
                    self.tableName, self.where)

    def __repr__(self):
        return self.__str__()

class InsertInto:
    def __init__(self, tableName, columnValueMap):
        self.tableName = tableName
        self.columnValueMap = columnValueMap

class Where:
    def __init__(self, condition):
        self.condition = condition

    def __str__(self):
        return "1=1" #todo

class Column:
    def __init__(self, name, type, size):
        self.name = name
        self.type = type
        self.size = size

    def __str__(self):
        return "Column(name: {}, type: {}, size: {})"\
                .format(self.name, self.type, self.size)

    def __repr__(self):
       return self.__str__()

class CreateTable():
    def __init__(self,table):
        self.table = table

class Table:
    def __init__(self, name, cols):
        self.name = name
        self.cols = cols
        self.current_row_id = 0

    def __str__(self):
        return "Table(name: {}, cols: {})".format(self.name, self.cols)

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

class StatementParser:
    def __init__(self, sql_string):
        self.statement = sqlparse.parse(sql_string)[0]
        self.idx = 0
        self.type = str(self.next_by_type(T.Keyword))

    def parse(self):
        if self.type == "CREATE":
            return self.CREATE_TABLE()
        elif self.type == "INSERT":
            return self.INSERT_INTO()
        elif self.type == "SELECT":
            return self.SELECT()
        else:
            return None #throw exception?

    def next_by_type(self, ttypes):
        if not isinstance(ttypes, (list, tuple)):
            ttypes = [ttypes]

        for i in range(len(self.statement.tokens[self.idx:])):
            i += self.idx
            if self.statement.tokens[i].ttype in ttypes:
                self.idx = i+1
                return self.statement.tokens[i]

    def next_by_instance(self, clss):
        if not isinstance(clss, (list, tuple)):
            clss = (clss,)

        for i in range(len(self.statement.tokens[self.idx:])):
            i += self.idx
            if isinstance(self.statement.tokens[i], clss):
                self.idx = i+1
                return self.statement.tokens[i]

    def INSERT_INTO(self):
        func = self.next_by_instance(sql.Function)

        tableName = str(func.token_first(ignore_comments=True))

        params = list(func.get_parameters())

        values_parenthesis = self.next_by_instance(sql.Parenthesis)

        identifier = list(values_parenthesis.get_sublists())[0]

        if isinstance(identifier,sql.IdentifierList):
            values = list(identifier.get_identifiers())
        else:
            values = [identifier]

        map = {}
        for i in range(len(params)):
            map[str(params[i])] = str(values[i])

        return InsertInto(tableName, map)

    @staticmethod
    def remove_quotes(str):
        if not str:
            return str
        if str[0] in ('"', '\'') and str[-1] == str[0]:
            str = str[1:-1]
        return str

    @staticmethod
    def get_operand(token):
        if isinstance(token, sql.Identifier):
            return Operand(Operand.OperandType.COLUMN,token.value)
        else:
            return Operand(Operand.OperandType.LITERAL,
                           StatementParser.remove_quotes(token.value))

    def SELECT(self):
        wildcard = self.statement.token_next_by_type(0, T.Wildcard)
        if wildcard is None:
            cols = []
            col_tokens = self.next_by_instance(sql.IdentifierList)

            for t in col_tokens.get_identifiers():
                cols.append(str(t))
        else:
            cols = None #means wildcard

        tableName = str(self.next_by_instance(sql.Identifier))

        where = self.next_by_instance(sql.Where)

        if where is not None:
            cmp = where.token_next_by_instance(0, sql.Comparison)

            left  = StatementParser.get_operand(cmp.left)
            operator = cmp.token_next_by_type(0, T.Comparison).value
            right = StatementParser.get_operand(cmp.right)

            condition = Condition(left=left, operator=operator, right=right)

            where = Where(condition)

        return Select(tableName=tableName, cols=cols, where=where)

    def CREATE_TABLE(self):
        func = self.next_by_instance(sql.Function)

        table_name = str(func.token_first())

        params = func.token_next_by_instance(0,sql.Parenthesis)

        params = str(params)[1:-1]
        params = params.split(',')

        cols = []
        for i in range(len(params)):
            params[i] = params[i].strip()
            (name, type) = params[i].split(' ')

            if type[-1] is ')':
                (type, size) = type[:-1].split('(')
                size = int(size)
            else:
                size = 4 #todo int for now

            cols.append(Column(name,type,size))

        return CreateTable(Table(table_name, cols))