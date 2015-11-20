"""
GraphFrontEndDataBaseWriter
"""
# front end common imports
from spinn_front_end_common.utilities.database.\
    database_writer import DatabaseWriter

# general imports
import logging
import traceback


logger = logging.getLogger(__name__)


class GraphFrontEndDataBaseWriter(DatabaseWriter):
    """
    GraphFrontEndDataBaseWriter: the interface for the database system for the
    spynnaker front end
    """

    def __init__(self, database_directory):
        DatabaseWriter.__init__(self, database_directory)

    def create_partitioned_atom_to_event_id_mapping(
            self, partitioned_graph, routing_infos):
        """

        :param partitioned_graph:
        :param routing_infos:
        :return:
        """

        # noinspection PyBroadException
        try:
            import sqlite3 as sqlite
            connection = sqlite.connect(self._database_path)
            cur = connection.cursor()
            # create table
            self._done_mapping = True
            cur.execute(
                "CREATE TABLE event_to_atom_mapping("
                "vertex_id INTEGER, atom_id INTEGER, "
                "event_id INTEGER PRIMARY KEY, "
                "FOREIGN KEY (vertex_id)"
                " REFERENCES Partitioned_vertices(vertex_id))")

            # insert into table
            vertices = list(partitioned_graph.subvertices)
            for partitioned_vertex in partitioned_graph.subvertices:
                out_going_edges = (partitioned_graph
                                   .outgoing_subedges_from_subvertex(
                                       partitioned_vertex))
                if len(out_going_edges) > 0:
                    routing_info = (routing_infos
                                    .get_subedge_information_from_subedge(
                                        out_going_edges[0]))
                    vertex_id = vertices.index(partitioned_vertex) + 1
                    event_ids = routing_info.get_keys()
                    for key in event_ids:
                        cur.execute(
                            "INSERT INTO event_to_atom_mapping("
                            "vertex_id, event_id, atom_id) "
                            "VALUES ({}, {}, {})"
                            .format(vertex_id, key, 0))
            connection.commit()
            connection.close()
        except Exception:
            traceback.print_exc()