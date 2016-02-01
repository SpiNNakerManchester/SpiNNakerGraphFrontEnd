
# front end common imports
from spinn_front_end_common.utilities.database.\
    database_writer import DatabaseWriter

# general imports
import logging
import traceback


logger = logging.getLogger(__name__)


class GraphFrontEndDataBaseWriter(DatabaseWriter):
    """ The interface for the database system
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
                partitions = partitioned_graph.\
                    outgoing_edges_partitions_from_vertex(partitioned_vertex)
                for partition in partitions:
                    event_ids = routing_infos.\
                        get_keys_and_masks_from_partition(partition)[0].keys
                    vertex_id = vertices.index(partitioned_vertex) + 1
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
