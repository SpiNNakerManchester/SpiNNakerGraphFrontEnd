__author__ = 'gmtuca'

class Entry:
    def __init__(self, row_id, col, value, response_time=-1):
        self.row_id = row_id
        self.col = col
        self.value = value
        self.response_time = response_time

    def __str__(self):
        return "Entry(row_id: {}, col: {}, value: {}, response_time: {})"\
            .format(self.row_id, self.col, self.value, self.response_time)

    def __repr__(self):
        return self.__str__()

class Row(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.firstResponseTime = 9999
        self.lastResponseTime = -1

    def __setitem__(self, colname, entry):
        dict.__setitem__(self, colname, entry)
        if entry.response_time > self.lastResponseTime:
            self.lastResponseTime = entry.response_time
        if entry.response_time < self.firstResponseTime:
            self.firstResponseTime = entry.response_time

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

    def ljust_str(self,longest_str_for_col):
        str = ""
        for c, e in self.iteritems():
            str += "  {}  ".format(e.value.ljust(longest_str_for_col[c]))
        return str

class Result:
    def __init__(self, success=True, rows={}):
        self.success = success
        self.rows = rows
        self.firstResponseTime = 9999
        self.lastResponseTime = -1

    def addEntry(self,e):
        row = self.rows.get(e.row_id)

        if row is None:
            row = Row()
            self.rows[e.row_id] = row
            if e.response_time < self.firstResponseTime:
                self.firstResponseTime = e.response_time

        if e.response_time > self.lastResponseTime:
            self.lastResponseTime = e.response_time

        row[e.col] = e

    def __str__(self):
        str =  "Response time:{0:.3f}ms\n".format(self.lastResponseTime)
        str += "Number of rows: {}\n\n".format(len(self.rows))

        if len(self.rows) == 0:
            return str

        longest_str_for_col = {}

        for row_id, row in self.rows.iteritems():
            for c, e in row.iteritems():
                if longest_str_for_col.get(c) is None or len(e.value) > longest_str_for_col[c]:
                    longest_str_for_col[c] = len(e.value)

        header = ""
        for row_id, row in self.rows.iteritems():
            header += "|"
            for c in row.keys():
                if len(c) > longest_str_for_col[c]:
                    longest_str_for_col[c] = len(c)
                header += "  {}  ".format(c.ljust(longest_str_for_col[c]))
            header += "|"
            break

        n_spaces = 0
        for l in longest_str_for_col.values():
            n_spaces += l + 4

        str += " " + "-" * n_spaces + " "
        str += '\n'
        str += header
        str += "\n"
        str += "|" + "-" * n_spaces + "|"
        str += "\n"

        for row_id, row in self.rows.iteritems():
            str += "|{}|\n".format(row.ljust_str(longest_str_for_col))

        str += " " + "-" * n_spaces + " "

        return str