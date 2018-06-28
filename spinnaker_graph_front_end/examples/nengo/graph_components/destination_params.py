

class DestinationParams(object):

    __slots__ = [
        '_dest_vertex',
        '_dest_port'
    ]

    def __init__(self, dest_vertex, dest_port):
        self._dest_vertex = dest_vertex
        self._dest_port = dest_port

    @property
    def dest_vertex(self):
        return self._dest_vertex

    @property
    def dest_port(self):
        return self._dest_port

    def __repr__(self):
        return "{}:{}".format(self._dest_port, self._dest_vertex)

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash((self._dest_port, self._dest_vertex))

    def __eq__(self, other):
        return (isinstance(other, DestinationParams) and
                self._dest_vertex == other.dest_vertex and
                self._dest_port == other.dest_port)

    def __ne__(self, other):
        return not self.__eq__(other)
