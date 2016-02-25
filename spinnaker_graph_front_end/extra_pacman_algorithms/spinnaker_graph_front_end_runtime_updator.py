
# pacman imports
from pacman.utilities.utility_objs.progress_bar import ProgressBar

# spinn front end common imports
from spinn_front_end_common.abstract_models.\
    abstract_data_specable_vertex import AbstractDataSpecableVertex
from spinn_front_end_common.utilities import exceptions as common_exceptions

# spinn graph fromnt end imports
from spinnaker_graph_front_end.abstract_partitioned_data_specable_vertex import \
    AbstractPartitionedDataSpecableVertex

# general imports
import math
import logging

logger = logging.getLogger(__name__)


class SpiNNakerGraphFrontEndRuntimeUpdator(object):
    """
    SpiNNakerGraphFrontEndRuntimeUpdator: updates the application graph with
    new runtimes (used by multi-run and initial runs)
    """

    def __call__(
            self, run_time, partitionable_graph, partitioned_graph,
            current_run_ms, ran_token=None):

        if ran_token is not None and not ran_token:
            raise common_exceptions.ConfigurationException(
                "This model can only run once the application has ran")

        progress_bar = ProgressBar(
            len(partitionable_graph.vertices) +
            len(partitioned_graph.subvertices),
            "Updating python vertices runtime")

        if run_time is not None:
            if current_run_ms is not None:
                run_time += current_run_ms
            for vertex in partitionable_graph.vertices:
                if isinstance(vertex, AbstractDataSpecableVertex):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
                progress_bar.update()
            for vertex in partitioned_graph.subvertices:
                if (isinstance(
                        vertex, AbstractPartitionedDataSpecableVertex) or
                        isinstance(vertex, AbstractDataSpecableVertex)):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
                progress_bar.update()
        else:
            self._no_machine_time_steps = None
            logger.warn("You have set a runtime that will never end, this may"
                        "cause the application models to fail to partition "
                        "correctly")
        progress_bar.end()
        return run_time

    def _set_runtime_in_time_steps_for_model(self, vertex, run_time):
        """

        :param vertex:
        :param run_time:
        :return:
        """
        self._no_machine_time_steps =\
            int((run_time * 1000.0) / vertex.machine_time_step)
        ceiled_machine_time_steps = \
            math.ceil((run_time * 1000.0) / vertex.machine_time_step)
        if self._no_machine_time_steps != ceiled_machine_time_steps:
            raise common_exceptions.ConfigurationException(
                "The runtime and machine time step combination "
                "result in a fractional number of machine runnable "
                "time steps and therefore spinnaker cannot "
                "determine how many to run for")
        vertex.set_no_machine_time_steps(self._no_machine_time_steps)

