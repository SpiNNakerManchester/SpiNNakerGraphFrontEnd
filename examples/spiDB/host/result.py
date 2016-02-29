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

    def __xyp__(self):
        return self.x, self.y, self.p

    def __str__(self):
        return "{:.3f}ms\t{} - {}: {}\t({},{},{}) {}"\
            .format(self.response_time, self.id, self.cmd,
                    "OK" if self.success else "FAIL",
                    self.x, self.y, self.p,
                    "" if self.data is None else " > {}".format(self.data)
                    )

    def __repr__(self):
        return self.__str__()

class Entry():
    def __init__(self, type, size, value):
        self.type = type
        self.size = size
        self.value = value

    def __str__(self):
        return "{} ({})"\
            .format(self.value, self.type)

    def __repr__(self):
        return self.__str__()

class SelectEntry(Entry):
    def __init__(self, row_id, col, size, type, value):
        Entry.__init__(self, type=type, size=size, value=value)
        self.row_id = row_id
        self.col = col

    def __str__(self):
        return "{}: ({}, {})"\
            .format(self.row_id, self.col, self.value)

class Row(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.origin = None

    def __setitem__(self, colname, type_value):
        dict.__setitem__(self, colname, type_value)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

class Result:
    def __init__(self):
        self.responses = list()

    def addResponse(self, r):
        self.responses.append(r)

    def __str__(self):
        if not self.responses:
            return "No Response\n"
        if len(self.responses) is 1:
            return "{}\n".format(str(self.responses[0]))
        return "{}\n".format(str(self.responses))

class PutResult(Result):
    def __init__(self):
        Result.__init__(self)

    def addResponse(self, r):
        Result.addResponse(self, r)

class PullResult(Result):
    def __init__(self):
        Result.__init__(self)

    def addResponse(self, r):
        Result.addResponse(self, r)

    def __str__(self):
        s = "PULL \n"
        for r in self.responses:
            s += "  {}\n".format(r)
        return s

    def __repr__(self):
        return self.__str__()

class InsertIntoResult(Result):
    def __init__(self):
        Result.__init__(self)

    def addResponse(self, r):
        Result.addResponse(self, r)

    def __str__(self):
        s = "INSERT_INTO\n"
        for r in self.responses:
            s += "  {}\n".format(r)
        return s

    def __repr__(self):
        return self.__str__()

class SelectResult(Result):
    def __init__(self):
        Result.__init__(self)
        self.rowidToRow = {}
        self.cols = set()

    def addResponse(self, r):
        Result.addResponse(self, r)

        e = r.data

        row = self.rowidToRow.get(e.row_id)

        if row is None:
            row = Row()
            row.origin = r.__xyp__()
            self.rowidToRow[e.row_id] = row

        if e.col not in self.cols: #we have not seen that column before
            self.cols.add(e.col)

        if row.get(e.col) is None:
            #first time we see that database entry (row-col)
            if cmp(row.origin, r.__xyp__()) is not 0:
                #row based, so all entries for that row
                # should come from the same xyp
                raise Exception("row.origin: {} != r.__xyp__()"
                                .format(row.origin, r.__xyp__()))
            row[e.col] = (e.type, e.value)
        else:
            raise Exception("Row with id '{}' on '{}' already exists " \
                            "with value '{}' from {}."\
                            .format(e.row_id, e.col, row[e.col], r.__xyp__()))

    def __repr__(self):
        return "{}, rows: {}"\
            .format(Result.__repr__(self), len(self.rowidToRow))

    def __str__(self):
        #metadata = "\nResponse time:{:.3f}ms\n".format(self.lastResponseTime)
        metadata = ""

        n_rows = len(self.rowidToRow)
        metadata += "Number of rows: {}\n".format(n_rows)

        metadata += self.responses.__repr__()

        if n_rows == 0:
            return metadata

        longest_str_for_col = {}

        for row_id, row in self.rowidToRow.iteritems():
            for c, t_v in row.iteritems():
                type, value = t_v
                #default integer characters size is 3
                m_size = 3 if type == 'integer' else len(value)
                if longest_str_for_col.get(c) is None \
                    or m_size > longest_str_for_col[c]:
                    longest_str_for_col[c] = m_size

        header = "|"
        for c in self.cols:
            if len(c) > longest_str_for_col[c]:
                longest_str_for_col[c] = len(c)
            header += "  {}  ".format(c.ljust(longest_str_for_col[c]))
        header += "|  (x, y, p)"

        n_spaces = 0
        for l in longest_str_for_col.values():
            n_spaces += l + 4

        table = " " + "-" * n_spaces + " " \
                "\n" + header + "\n" \
                "|" + "-" * n_spaces + "|" \
                "\n"

        found_entries = 0
        #expected_entries = n_rows * len(self.cols)

        for row_id, row in self.rowidToRow.iteritems():
            table += "|"
            for c in self.cols:
                type, value = row.get(c)
                if value is None:
                    table += "  {}  ".format("".ljust(longest_str_for_col[c]))
                else:
                    found_entries += 1
                    table += "  {}  "\
                        .format(str(value).ljust(longest_str_for_col[c]))

            table += "|  {}\n".format(row.origin)

        table += " " + "-" * n_spaces + " "

        metadata += "Number of entries: {}\n"\
            .format(found_entries)

        return metadata + table

    @property
    def entriesFound(self):
        e = 0
        for row_id, row in self.rowidToRow.iteritems():
            for c in self.cols:
                if row.get(c) is not None:
                    e += 1
        return e