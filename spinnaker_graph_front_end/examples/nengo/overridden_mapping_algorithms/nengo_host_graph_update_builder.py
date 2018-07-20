from spinn_front_end_common.utilities.database import DatabaseConnection
from spinnaker_graph_front_end.examples.nengo.io_connections.\
    nengo_host_graph_updater import \
    NengoHostGraphUpdater


class NengoHostGraphUpdateBuilder(object):

    def __call__(self, nengo_host_graph, time_step):

        nengo_host_graph_updater = NengoHostGraphUpdater(
            nengo_host_graph, time_step)

        auto_pause_and_resume_interface = DatabaseConnection(
            start_resume_callback_function=(
                nengo_host_graph_updater.start_resume),
            stop_pause_callback_function=(
                nengo_host_graph_updater.pause_stop))

        return auto_pause_and_resume_interface, nengo_host_graph_updater
