"""
SpinnakerGraphFrontEndDatabaseInterface
"""

# pacman imports
from pacman.utilities.utility_objs.progress_bar import ProgressBar

# front end common imports
from spinn_front_end_common.utilities import helpful_functions

# graph front end imports
from spynnaker_graph_front_end.utilities.database.\
    graph_front_end_database_writer import GraphFrontEndDataBaseWriter


class SpinnakerGraphFrontEndDatabaseInterface(object):
    """
    SpinnakerGraphFrontEndDatabaseInterface
    """
    
    def __init__(self):
        self._writer = None
    
    def __call__(
            self, partitioned_graph, user_create_database, tags,
            runtime, machine, time_scale_factor, machine_time_step,
            placements, routing_infos, router_tables, execute_mapping,
            database_directory, wait_for_read_confirmation, socket_addresses):
        
        self._writer = GraphFrontEndDataBaseWriter(
            database_directory, wait_for_read_confirmation, socket_addresses)
        
        # add database generation if requested
        needs_database = \
            helpful_functions.auto_detect_database(partitioned_graph)
        if ((user_create_database == "None" and needs_database) or
                user_create_database == "True"):

            database_progress = ProgressBar(8, "Creating database")

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
            self._writer.send_read_notification()

        return {"database_interface": self}
    
    def wait_for_confirmation(self):
        """

        :return:
        """
        self._writer.wait_for_confirmation()

    def send_read_notification(self):
        """
        helper method for sending the read notifcations from the notification
        protocol
        :return:
        """
        self._writer.send_read_notification()

    def send_start_notification(self):
        """
        helper method for sending the start notifcations from the notification
        protocol
        :return:
        """
        self._writer.send_start_notification()
