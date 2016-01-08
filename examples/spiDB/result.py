__author__ = 'gmtuca'

class Response:
    def __init__(self, id, success, cmd, x, y, p):
        self.id = id
        self.success = success
        self.cmd = cmd
        self.x = x
        self.y = y
        self.p = p
        self.response_time = -1
        self.data = None

    def __str__(self):
        return "{} ({},{},{})"\
            .format("OK" if self.success else "FAIL", self.x, self.y, self.p)

class Entry():
    def __init__(self, row_id, col, value):
        self.row_id = row_id
        self.col = col
        self.value = value

    def __str__(self):
        return "Entry(row_id: {}, col: {}, value: {})"\
            .format(self.row_id, self.col, self.value)

    def __repr__(self):
        return self.__str__()

class Row(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        """
        self.firstResponseTime = 9999
        self.lastResponseTime = -1
        """

    def __setitem__(self, colname, entry):
        dict.__setitem__(self, colname, entry)
        """
        if entry.response_time > self.lastResponseTime:
            self.lastResponseTime = entry.response_time
        if entry.response_time < self.firstResponseTime:
            self.firstResponseTime = entry.response_time
        """

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

    def ljust_str(self,longest_str_for_col):
        str = ""
        for c, v in self.iteritems():
            str += "  {}  ".format(v.ljust(longest_str_for_col[c]))
        return str


class Result:
    def __init__(self):
        self.firstResponseTime = 9999
        self.lastResponseTime = -1
        self.responses = list()

    def addResponse(self, r):
        if r.response_time < self.firstResponseTime:
            self.firstResponseTime = r.response_time
        if r.response_time > self.lastResponseTime:
            self.lastResponseTime = r.response_time
        self.responses.append(r)

    def __repr__(self):
        return "responses: {}"\
            .format(len(self.responses))

class SelectResult(Result):
    def __init__(self):
        Result.__init__(self)
        self.rows = {}

    def addResponse(self, r):
        Result.addResponse(self, r)

        e = r.data

        row = self.rows.get(e.row_id)

        if row is None:
            row = Row()
            self.rows[e.row_id] = row

        if row.get(e.col) is not None:
            raise Exception("Column {} already exists with value {}."
                            "Unable to insert value {}",
                            e.col, row[e.col], e.value)

        row[e.col] = e.value

    def __repr__(self):
        return "{}, rows: {}".format(Result.__repr__(self), len(self.rows))

    def __str__(self):
        #str =  "Response time:{0:.3f}ms\n".format(self.lastResponseTime)
        #str += "Number of rows: {}\n\n".format(len(self.rows))

        if len(self.rows) == 0:
            return "*empty*"

        str = ""

        longest_str_for_col = {}

        for row_id, row in self.rows.iteritems():
            for c, v in row.iteritems():
                if longest_str_for_col.get(c) is None or len(v) > longest_str_for_col[c]:
                    longest_str_for_col[c] = len(v)

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