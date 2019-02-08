from spinn_front_end_common.utilities.failed_state import FailedState
from spinnaker_graph_front_end.graph_front_end_simulator_interface import (
    GraphFrontEndSimulatorInterface)


class GraphFrontEndFailedState(GraphFrontEndSimulatorInterface, FailedState):

    __slots__ = ()
