
# pacman imports
from pacman.utilities.utility_objs.progress_bar import ProgressBar

# front end common imports
from spinn_front_end_common.utilities import helpful_functions

# graph front end imports
from spinnaker_graph_front_end.utilities.database.\
    graph_front_end_database_writer import GraphFrontEndDataBaseWriter


class SpinnakerGraphFrontEndDatabaseInterface(object):

    def __init__(self):
        self._writer = None
        self._user_create_database = None
        self._needs_database = None

    def __call__(
            self, partitioned_graph, user_create_database, tags,
            runtime, machine, time_scale_factor, machine_time_step,
            placements, routing_infos, router_tables, execute_mapping,
            database_directory):

        self._needs_database = \
            helpful_functions.auto_detect_database(partitioned_graph)
        self._user_create_database = user_create_database

        if ((self._user_create_database == "None" and self._needs_database) or
                self._user_create_database == "True"):

            database_progress = ProgressBar(8, "Creating database")

            self._writer = GraphFrontEndDataBaseWriter(database_directory)

            self._writer.add_system_params(
                time_scale_factor, machine_time_step, runtime)
            database_progress.update()
            self._writer.add_machine_objects(machine)
            database_progress.update()
            self._writer.add_placements(placements, partitioned_graph)
            database_progress.update()
            self._writer.add_routing_infos(
                routing_infos, partitioned_graph)
            database_progress.update()
            self._writer.add_routing_tables(router_tables)
            database_progress.update()
            self._writer.add_tags(partitioned_graph, tags)
            database_progress.update()
            if execute_mapping:
                self._writer.create_partitioned_atom_to_event_id_mapping(
                    partitioned_graph=partitioned_graph,
                    routing_infos=routing_infos)
            database_progress.update()
            database_progress.update()
            database_progress.end()

        return {"database_interface": self,
                "database_file_path": self.database_file_path}

    @property
    def database_file_path(self):
        """

        :return:
        """
        if ((self._user_create_database == "None" and self._needs_database) or
                self._user_create_database == "True"):
            return self._writer.database_path
