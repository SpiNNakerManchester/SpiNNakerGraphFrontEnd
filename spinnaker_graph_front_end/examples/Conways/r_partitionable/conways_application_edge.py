from pacman.model.decorators.overrides import overrides
from pacman.model.graphs.application.impl.application_edge import \
    ApplicationEdge

from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_list_connector import ConwaysListConnector
from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_machine_edge import ConwaysMachineEdge

import logging

from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_synapse_dynamics import ConwaysSynapseDynamics
from spynnaker.pyNN import ProjectionApplicationEdge
from spynnaker.pyNN.models.neural_projections.synapse_information import \
    SynapseInformation

logger = logging.getLogger(__name__)


class ConwaysApplicationEdge(ProjectionApplicationEdge):
    """ An edge which terminates on an AbstractPopulationVertex
    """

    def __init__(
            self, pre_vertex, post_vertex, grid_x_size, grid_y_size, 
            label=None):
        ApplicationEdge.__init__(
            self, pre_vertex, post_vertex, label=label)

        # A list of all synapse information for all the projections that are
        # represented by this edge
        conn_list = list()
        for x in range(0, grid_x_size):
            for y in range(0, grid_y_size):

                positions = [
                    (x, (y + 1) % grid_y_size, "N"),
                    ((x + 1) % grid_x_size,
                     (y + 1) % grid_y_size, "NE"),
                    ((x + 1) % grid_x_size, y, "E"),
                    ((x + 1) % grid_x_size,
                     (y - 1) % grid_y_size, "SE"),
                    (x, (y - 1) % grid_y_size, "S"),
                    ((x - 1) % grid_x_size,
                     (y - 1) % grid_y_size, "SW"),
                    ((x - 1) % grid_x_size, y, "W"),
                    ((x - 1) % grid_x_size,
                     (y + 1) % grid_y_size, "NW")]

                for (dest_x, dest_y, compass) in positions:
                    conn_list.append((
                        x + (y * grid_y_size),
                        dest_x + (dest_y * grid_y_size)))

        self._synapse_information = SynapseInformation(
            ConwaysListConnector(conn_list), ConwaysSynapseDynamics(), 0)

        self._stored_synaptic_data_from_machine = None

    @property
    def synapse_information(self):
        return [self._synapse_information]

    @property
    def delay_edge(self):
        return None

    @property
    def n_delay_stages(self):
        return 0

    @overrides(ApplicationEdge.create_machine_edge)
    def create_machine_edge(
            self, pre_vertex, post_vertex, label):


        return ConwaysMachineEdge(
            self._synapse_information, pre_vertex, post_vertex, label)
