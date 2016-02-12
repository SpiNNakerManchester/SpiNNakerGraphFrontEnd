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
        return "({}){}: {} ({},{},{})"\
            .format(self.id, self.cmd, "OK" if self.success else "FAIL", self.x, self.y, self.p)

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
        self.origin = None
        """
        self.firstResponseTime = 9999
        self.lastResponseTime = -1
        """

    def __setitem__(self, colname, value):
        dict.__setitem__(self, colname, value)
        """
        if entry.response_time > self.lastResponseTime:
            self.lastResponseTime = entry.response_time
        if entry.response_time < self.firstResponseTime:
            self.firstResponseTime = entry.response_time
        """

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

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

    def __str__(self):
        return str(self.responses[0]) if len(self.responses) > 0 else "No response"

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

        if row.get(e.col) is None: #first time we see that database entry (row-col)
            if cmp(row.origin, r.__xyp__()) is not 0: #row based, so all entries for that row should come from the same xyp
                raise Exception("row.origin: {} != r.__xyp__()".format(row.origin, r.__xyp__()))
            row[e.col] = e.value
        else: #raise Exception()
            print "Row with id '{}' on '{}' already exists " \
                  "with value '{}' from {}."\
                .format(e.row_id, e.col, row[e.col], r.__xyp__())

    def getRows(self):
        return self.rowidToRow.values()

    def __repr__(self):
        return "{}, rows: {}".format(Result.__repr__(self), len(self.rowidToRow))

    def __str__(self):
        metadata = "\nResponse time:{0:.3f}ms\n".format(self.lastResponseTime)

        n_rows = len(self.rowidToRow)
        metadata += "Number of rows: {}\n".format(n_rows)

        if n_rows == 0:
            return metadata

        longest_str_for_col = {}

        for row_id, row in self.rowidToRow.iteritems():
            for c, v in row.iteritems():
                if longest_str_for_col.get(c) is None or len(v) > longest_str_for_col[c]:
                    longest_str_for_col[c] = len(v)

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
        expected_entries = n_rows * len(self.cols)

        for row_id, row in self.rowidToRow.iteritems():
            table += "|"
            for c in self.cols:
                v = row.get(c)
                if v is None:
                    table += "  {}  ".format("".ljust(longest_str_for_col[c]))
                else:
                    found_entries += 1
                    table += "  {}  ".format(v.ljust(longest_str_for_col[c]))

            table += "|  {}\n".format(row.origin) #- id: {} , row_id

        table += " " + "-" * n_spaces + " "

        metadata += "Number entries found: {}/{} ({}%) \n"\
            .format(found_entries, expected_entries,
                    (100.0*found_entries)/expected_entries)

        return metadata + table

    @property
    def entriesFound(self):
        e = 0
        for row_id, row in self.rowidToRow.iteritems():
            for c in self.cols:
                if row.get(c) is not None:
                    e += 1
        return e