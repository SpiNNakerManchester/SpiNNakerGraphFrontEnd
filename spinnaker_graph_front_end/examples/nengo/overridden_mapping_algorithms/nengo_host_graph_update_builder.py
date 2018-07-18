import time

from spinn_front_end_common.utilities.connections import LiveEventConnection
from spinnaker_graph_front_end.examples.nengo.io_connections.\
    nengo_host_graph_updater import \
    NengoHostGraphUpdater


class NengoHostGraphUpdateBuilder(object):

    SLEEP_PERIOD = 0.0001

    def __call__(self, nengo_host_graph, time_step):

        auto_pause_and_resume_interface = LiveEventConnection(
            live_packet_gather_label="NengoStreamOutGatherer")
        nengo_host_graph_updater = NengoHostGraphUpdater(
            nengo_host_graph, time_step)
        auto_pause_and_resume_interface.add_start_resume_callback(
            "host_network", nengo_host_graph_updater.start_resume)
        auto_pause_and_resume_interface.add_pause_stop_callback(
            "host_network", nengo_host_graph_updater.pause_stop)
