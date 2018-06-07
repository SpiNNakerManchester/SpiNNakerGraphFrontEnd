from collections import defaultdict
from spinn_utilities.ordered_set import OrderedSet


class GraphMapper(object):
    """ A mapping between an Application Graph and a Machine Graph
    """

    __slots__ = [

        # dict of machine vertex -> application vertex
        "_application_vertex_by_machine_vertex",

        # dict of machine edge -> application edge
        "_application_edge_by_machine_edge",

        # dict of application vertex -> set of machine vertices
        "_machine_vertices_by_application_vertex",

        # dict of application edge -> set of machine edges
        "_machine_edges_by_application_edge",

        # dict of machine vertex -> index of vertex in list of vertices from
        #                           the same application vertex
        "_index_by_machine_vertex",
    ]

    def __init__(self):
        self._application_vertex_by_machine_vertex = dict()
        self._application_edge_by_machine_edge = dict()

        self._machine_vertices_by_application_vertex = defaultdict(OrderedSet)
        self._machine_edges_by_application_edge = defaultdict(OrderedSet)

        self._index_by_machine_vertex = dict()

    def add_vertex_mapping(
            self, machine_vertex, application_vertex):
        """ Add a mapping between application and machine vertices

        :param machine_vertex: A vertex from a Machine Graph
        :param application_vertex: A vertex from an Application Graph
        """
        self._application_vertex_by_machine_vertex[machine_vertex] = \
            application_vertex
        machine_vertices = self._machine_vertices_by_application_vertex[
            application_vertex]
        self._index_by_machine_vertex[machine_vertex] = len(machine_vertices)
        machine_vertices.add(machine_vertex)

    def add_edge_mapping(self, machine_edge, application_edge):
        """ Add a mapping between a machine edge and an application edge

        :param machine_edge: An edge from a Machine Graph
        :param application_edge: An edge from an Application Graph
        """
        self._machine_edges_by_application_edge[application_edge].add(
            machine_edge)
        self._application_edge_by_machine_edge[machine_edge] = application_edge

    def get_machine_vertices(self, application_vertex):
        """ Get all machine vertices mapped to a given application vertex

        :param application_vertex: A vertex from an Application Graph
        :return: An iterable of machine vertices or None if none
        """
        return self._machine_vertices_by_application_vertex.get(
            application_vertex, None)

    def get_machine_vertex_index(self, machine_vertex):
        """ Get the index of a machine vertex within the list of such vertices\
            associated with an application vertex
        """
        return self._index_by_machine_vertex[machine_vertex]

    def get_machine_edges(self, application_edge):
        """ Get all machine edges mapped to a given application edge

        :param application_edge: An edge from an Application Graph
        :return: An iterable of machine edges or None if none
        """
        return self._machine_edges_by_application_edge.get(
            application_edge, None)

    def get_application_vertex(self, machine_vertex):
        """ Get the application vertex mapped to a machine vertex

        :param machine_vertex: A vertex from a Machine Graph
        :return: an application vertex, or None if none
        """
        return self._application_vertex_by_machine_vertex.get(
            machine_vertex, None)

    def get_application_edge(self, machine_edge):
        """ Get the application edge mapped to a machine edge

        :param machine_edge: An edge from a Machine Graph
        :return: A machine edge, or None if none
        """
        return self._application_edge_by_machine_edge.get(machine_edge, None)
