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
    def __init__(self, cols=None, where=None):
        if cols is None:
            self.wildcard = True
        else:
            self.wildcard = False

        self.cols = cols
        self.where = where

class Where:
    def __init__(self, condition):
        self.condition = condition

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

    def generate_INSERT_INTO_map(self):
        func = self.next_by_instance(sql.Function)
        params = list(func.get_parameters())

        values_parenthesis = self.next_by_instance(sql.Parenthesis)
        values = list(list(values_parenthesis.get_sublists())[0].get_identifiers())

        map = {}
        for i in range(len(params)):
            map[str(params[i])] = str(values[i])

        return map

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
        where = self.next_by_instance(sql.Where)

        cmp = where.token_next_by_instance(0, sql.Comparison)

        left  = StatementParser.get_operand(cmp.left)
        operator = cmp.token_next_by_type(0, T.Comparison).value
        right = StatementParser.get_operand(cmp.right)

        condition = Condition(left=left, operator=operator, right=right)

        sel = Select(cols=None, where=Where(condition))

        return sel

    def CREATE_TABLE(self):
        func = self.next_by_instance(sql.Function)

        table_name = str(func.token_first(ignore_comments=True))

        func = str(func)

        i_parenthesis_open  = func.find('(')
        i_parenthesis_close = func.rfind(')')

        params = func[i_parenthesis_open+1:i_parenthesis_close-1].split(',')

        cols = []
        for i in range(len(params)):
            params[i] = params[i].strip()
            parts = params[i].split(' ')
            name = parts[0]

            i_parenthesis_open = parts[1].find('(')
            i_parenthesis_close = parts[1].find(')')
            type = parts[1][:i_parenthesis_open]

            if type == "varchar":
                size = int(parts[1][i_parenthesis_open+1:i_parenthesis_close])
            else:
                size = 4 #int for now todo other datatypes/sizes

            cols.append(Column(name,type,size))

        return Table(table_name, cols)


"""SELECT *
        FROM People
        WHERE name = 123;

        p = StatementParser(sel)
p.SELECT()
      """



"""
typedef struct Condition {
    uint8_t     col_index;
    Comparison  comparison;
    uchar*      value;
} Condition;

typedef struct Where {
    Condition  condition;
} Where;

typedef struct selectQuery {
    spiDBcommand cmd;
    uint32_t     id;

    Where        where;
    //simply do for SELECT * for now
} selectQuery;
"""