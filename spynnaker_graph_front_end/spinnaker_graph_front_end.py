"""
entrance class for the graph front end
"""
from pacman.model.partitionable_graph.partitionable_edge import \
    PartitionableEdge
from spinn_front_end_common.abstract_models.\
    abstract_data_specable_vertex import \
    AbstractDataSpecableVertex

from spinn_front_end_common.interface.\
    front_end_common_configuration_functions import \
    FrontEndCommonConfigurationFunctions
from spinn_front_end_common.interface.\
    front_end_common_interface_functions import \
    FrontEndCommonInterfaceFunctions
from spinn_front_end_common.utilities import reports
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.utilities.timer import Timer


from spynnaker_graph_front_end.utilities.xml_interface import XMLInterface
from spynnaker_graph_front_end.utilities import conf

import math
import logging


logger = logging.getLogger(__name__)


class SpiNNakerGraphFrontEnd(FrontEndCommonConfigurationFunctions,
                             FrontEndCommonInterfaceFunctions):
    """
    entrance class for the graph front end
    """

    def __init__(self):
        """
        generate a spinnaker grpah front end object
        :return: the spinnaker grpah front end object
        """


        FrontEndCommonConfigurationFunctions.__init__(self, host_name,
                                                      graph_label)
        FrontEndCommonInterfaceFunctions.__init__(self, report_folder,
                                                  report_states)
        self._none_labelled_vertex_count = 0
        self._none_labelled_edge_count = 0

    def add_vertex(self, cellclass, cellparams, label=None):
        if label is None:
            label = "Vertex {}".format(self._none_labelled_vertex_count)
            self._none_labelled_vertex_count += 1
        cellparams['label'] = label
        vertex = cellclass(**cellparams)
        self._partitionable_graph.add_vertex(vertex)

    def add_edge(self, pre_vertex, post_vertex, constraints, label):
        if label is None:
            label = "Edge {}".format(self._none_labelled_edge_count)
            self._none_labelled_edge_count += 1
        edge = PartitionableEdge(pre_vertex, post_vertex, constraints, label)

    def run(self, run_time):
        self._setup_interfaces(hostname=self._hostname)

        # create network report if needed
        if self._reports_states is not None:
            reports.network_specification_report(
                self._report_default_directory, self._partitionable_graph,
                self._hostname)

        # calculate number of machine time steps
        if run_time is not None:
            self._no_machine_time_steps =\
                int((run_time * 1000.0) / self._machine_time_step)
            ceiled_machine_time_steps = \
                math.ceil((run_time * 1000.0) / self._machine_time_step)
            if self._no_machine_time_steps != ceiled_machine_time_steps:
                raise exceptions.ConfigurationException(
                    "The runtime and machine time step combination result in "
                    "a factional number of machine runable time steps and "
                    "therefore spinnaker cannot determine how many to run for")
            for vertex in self._partitionable_graph.vertices:
                if isinstance(vertex, AbstractDataSpecableVertex):
                    vertex.set_no_machine_time_steps(
                        self._no_machine_time_steps)
        else:
            self._no_machine_time_steps = None
            logger.warn("You have set a runtime that will never end, this may"
                        "cause the neural models to fail to partition "
                        "correctly")
            for vertex in self._partitionable_graph.vertices:
                if vertex.is_set_to_record_spikes():
                    raise exceptions.ConfigurationException(
                        "recording a population when set to infinite runtime "
                        "is not currently supportable in this tool chain."
                        "watch this space")

        do_timing = conf.config.getboolean("Reports", "outputTimesForSections")
        if do_timing:
            timer = Timer()
        else:
            timer = None

        self.set_runtime(run_time)
        logger.info("*** Running Mapper *** ")
        if do_timing:
            timer.start_timing()
        self.map_model()
        if do_timing:
            timer.take_sample()

        # execute data spec generation
        if do_timing:
            timer.start_timing()
        logger.info("*** Generating Output *** ")
        logger.debug("")
        executable_targets = self.generate_data_specifications()
        if do_timing:
            timer.take_sample()

        # execute data spec execution
        if do_timing:
            timer.start_timing()
        processor_to_app_data_base_address = \
            self.execute_data_specification_execution(
                conf.config.getboolean("SpecExecution", "specExecOnHost"),
                self._hostname, self._placements, self._graph_mapper)

        if self._reports_states is not None:
            reports.write_memory_map_report(self._report_default_directory,
                                            processor_to_app_data_base_address)

        if do_timing:
            timer.take_sample()

        if do_timing:
            timer.start_timing()

        logger.info("*** Loading tags ***")
        self._load_iptags()
        self._load_reverse_ip_tags()

        if self._do_load is True:
            logger.info("*** Loading data ***")
            self._load_application_data(
                self._placements, self._router_tables, self._graph_mapper,
                processor_to_app_data_base_address, self._hostname,
                self._app_id)
            logger.info("*** Loading executables ***")
            self._load_executable_images(executable_targets, self._app_id)
        if do_timing:
            timer.take_sample()

        if self._do_run is True:
            logger.info("*** Running simulation... *** ")
            if self._reports_states.transciever_report:
                binary_folder = conf.config.get("SpecGeneration",
                                                "Binary_folder")
                reports.re_load_script_running_aspects(
                    binary_folder, executable_targets, self._hostname,
                    self._app_id, run_time)

            wait_on_confirmation = conf.config.getboolean(
                "Database", "wait_on_confirmation")
            send_start_notification = conf.config.getboolean(
                "Database", "send_start_notification")
            self._start_execution_on_machine(
                executable_targets, self._app_id, self._runtime,
                self._time_scale_factor, wait_on_confirmation,
                send_start_notification, self._in_debug_mode)
            self._has_ran = True
            if self._retrieve_provance_data:

                # retrieve provance data
                self._retieve_provance_data_from_machine(
                    executable_targets, self._router_tables, self._machine)

    def end(self):
        pass

    def read_xml_file(self, file_path):
        xml_interface = XMLInterface(file_path)
        self._partitionable_graph = xml_interface.read_in_file()