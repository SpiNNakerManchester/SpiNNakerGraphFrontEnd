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
from spynnaker_graph_front_end.utilities.conf import config

import math
import logging


logger = logging.getLogger(__name__)


class SpiNNakerGraphFrontEnd(FrontEndCommonConfigurationFunctions,
                             FrontEndCommonInterfaceFunctions):
    """
    entrance class for the graph front end
    """

    def __init__(self, hostname=None, graph_label=None,
                 model_binaries_path=None):
        """
        generate a spinnaker grpah front end object
        :return: the spinnaker graph front end object
        """
        global _binary_search_paths
        if model_binaries_path is not None:
            _binary_search_paths.add_path(model_binaries_path)

        if hostname is None:
            hostname = config.get("Machine", "machineName")
        if graph_label is None:
            graph_label = config.get("Application", "graph_label")

        FrontEndCommonConfigurationFunctions.__init__(self, hostname,
                                                      graph_label)

        application_file_folder = \
            config.get("Reports", "defaultApplicationDataFilePath")
        max_application_binaries = \
            config.get("Reports", "max_application_binaries_kept")
        max_reports_kept = config.get("Reports", "max_reports_kept")
        default_report_folder = \
            config.get("Reports", "defaultReportFilePath")
        enabled_reports = config.get("Reports", "reportsEnabled")
        write_provance = config.get("Reports", "writeProvanceData")
        write_text_spec = config.get("Reports", "writeTextSpecs")
        app_id = config.get("Application", "appID")
        execute_data_spec_report = \
            config.getboolean("Reports", "writeTextSpecs"),
        execute_partitioner_report = \
            config.getboolean("Reports", "writePartitionerReports"),
        execute_placer_report = \
            config.getboolean("Reports", "writePlacerReports"),
        execute_router_dat_based_report = \
            config.getboolean("Reports", "writeRouterDatReport"),
        generate_performance_measurements = \
            config.getboolean("Reports", "outputTimesForSections"),
        execute_router_report = \
            config.getboolean("Reports", "writeRouterReports"),
        execute_write_reload_steps = \
            config.getboolean("Reports", "writeReloadSteps"),
        generate_transciever_report = \
            config.getboolean("Reports", "writeTransceiverReport"),
        execute_routing_info_report = \
            config.getboolean("Reports", "writeRouterInfoReport"),
        in_debug_mode = config.get("Mode", "mode") == "Debug",
        create_database = config.getboolean("Database", "create_database")
        partitioner_algorithm = config.get("Partitioner", "algorithm")
        placer_algorithm = config.get("Placer", "algorithm")
        key_allocator_algorithm = config.get("KeyAllocator", "algorithm")
        router_algorithm = config.get("Routing", "algorithm")
        virtual_x_dimension = \
            config.get("Machine", "virutal_board_x_dimension"),
        virtual_y_dimension = \
            config.get("Machine", "virutal_board_y_dimension"),
        downed_chips = config.get("Machine", "down_chips"),
        downed_cores = config.get("Machine", "down_cores"),
        requires_virtual_board = config.getboolean("Machine", "virtual_board"),
        requires_wrap_around = config.get("Machine", "requires_wrap_arounds"),
        machine_version = config.getint("Machine", "version")
        # set up the configuration methods
        self._set_up_output_application_data_specifics(application_file_folder,
                                                       max_application_binaries)
        self._set_up_report_specifics(
            enabled_reports, write_text_spec, default_report_folder,
            max_reports_kept, write_provance)

        self._set_up_main_objects(
            app_id=app_id, create_database=create_database,
            execute_data_spec_report=execute_data_spec_report,
            execute_partitioner_report=execute_partitioner_report,
            execute_placer_report=execute_placer_report,
            execute_router_dat_based_report=execute_router_dat_based_report,
            execute_router_report=execute_router_report,
            execute_routing_info_report=execute_routing_info_report,
            execute_write_reload_steps=execute_write_reload_steps,
            generate_performance_measurements=generate_performance_measurements,
            generate_transciever_report=generate_transciever_report,
            in_debug_mode=in_debug_mode, reports_are_enabled=enabled_reports)
        
        self._set_up_pacman_algorthms_listings(
            partitioner_algorithm=partitioner_algorithm,
            placer_algorithm=placer_algorithm,
            key_allocator_algorithm=key_allocator_algorithm,
            routing_algorithm=router_algorithm)

        self._set_up_executable_specifics()

        #set up the interfaces with the machine
        FrontEndCommonInterfaceFunctions.__init__(self, default_report_folder,
                                                  self._reports_states)
        self._setup_interfaces(
            downed_chips=downed_chips, downed_cores=downed_cores,
            hostname=hostname, machine_version=machine_version,
            requires_virtual_board=requires_virtual_board,
            requires_wrap_around=requires_wrap_around,
            virtual_x_dimension=virtual_x_dimension,
            virtual_y_dimension=virtual_y_dimension)

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
        self._partitionable_graph.add_edge(edge)

    def run(self, run_time):
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

        do_timing = config.getboolean("Reports", "outputTimesForSections")
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
                config.getboolean("SpecExecution", "specExecOnHost"),
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
                binary_folder = config.get("SpecGeneration",
                                                "Binary_folder")
                reports.re_load_script_running_aspects(
                    binary_folder, executable_targets, self._hostname,
                    self._app_id, run_time)

            wait_on_confirmation = config.getboolean(
                "Database", "wait_on_confirmation")
            send_start_notification = config.getboolean(
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