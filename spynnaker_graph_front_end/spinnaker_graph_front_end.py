"""
entrance class for the graph front end
"""

# pacman imports
import traceback
from data_specification.data_specification_executor import \
    DataSpecificationExecutor
from data_specification.file_data_reader import FileDataReader
from data_specification.file_data_writer import FileDataWriter
from pacman.model.partitioned_graph.partitioned_graph import PartitionedGraph
from pacman.model.routing_info.dict_based_partitioned_edge_n_keys_map import \
    DictBasedPartitionedEdgeNKeysMap
from pacman.operations.partition_algorithms import BasicPartitioner
from pacman.operations.placer_algorithms import BasicPlacer
from pacman.operations.router_algorithms import BasicDijkstraRouting
from pacman.operations.router_check_functionality.valid_routes_checker import \
    ValidRouteChecker
from pacman.utilities import reports as pacman_reports
from pacman.operations.routing_info_allocator_algorithms import \
    BasicRoutingInfoAllocator
from pacman.operations.tag_allocator_algorithms import BasicTagAllocator
from pacman.utilities.progress_bar import ProgressBar
from spinn_front_end_common.abstract_models.\
    abstract_data_specable_vertex import \
    AbstractDataSpecableVertex
from spinn_front_end_common.interface.data_generator_interface import \
    DataGeneratorInterface

# spinn front end common imports
from spinn_front_end_common.interface.\
    front_end_common_configuration_functions import \
    FrontEndCommonConfigurationFunctions
from spinn_front_end_common.interface.\
    front_end_common_interface_functions import \
    FrontEndCommonInterfaceFunctions
from spinn_front_end_common.utilities import reports
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities.timer import Timer
from spinn_front_end_common.abstract_models.\
    abstract_provides_outgoing_edge_constraints \
    import AbstractProvidesOutgoingEdgeConstraints
from spinn_front_end_common.abstract_models.\
    abstract_provides_incoming_edge_constraints \
    import AbstractProvidesIncomingEdgeConstraints
from spinn_front_end_common.abstract_models.\
    abstract_provides_n_keys_for_edge import AbstractProvidesNKeysForEdge

# spinnman imports
from spinn_machine.virutal_machine import VirtualMachine
from spinnman.model.core_subset import CoreSubset
from spinnman.model.core_subsets import CoreSubsets
from spinnman.data.file_data_reader import FileDataReader \
    as SpinnmanFileDataReader

# spinn_machine imports
from spinn_machine.sdram import SDRAM

# graph front end imports
from spynnaker_graph_front_end.DataSpecedGeneratorInterface import \
    DataSpecedGeneratorInterface
from spynnaker_graph_front_end.abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex
from spynnaker_graph_front_end.models.\
    mutli_cast_partitioned_edge_with_n_keys import \
    MultiCastPartitionedEdgeWithNKeys
from spynnaker_graph_front_end.utilities.database.data_base_interface import \
    DataBaseInterface
from spynnaker_graph_front_end.utilities.database.socket_address import \
    SocketAddress
from spynnaker_graph_front_end.utilities.xml_interface import XMLInterface
from spynnaker_graph_front_end.utilities.conf import config

# general imports
import logging
import math
import os
from multiprocessing.pool import ThreadPool


logger = logging.getLogger(__name__)


class SpiNNakerGraphFrontEnd(FrontEndCommonConfigurationFunctions,
                             FrontEndCommonInterfaceFunctions):
    """
    entrance class for the graph front end
    """

    def __init__(self, hostname=None, graph_label=None,
                 executable_paths=None, database_socket_addresses=None):
        """
        generate a spinnaker grpah front end object
        :param hostname:
        :param graph_label:
        :param executable_paths:
        :return:the spinnaker graph front end object
        """

        if hostname is None:
            hostname = config.get("Machine", "machineName")
        if graph_label is None:
            graph_label = config.get("Application", "graph_label")

        if database_socket_addresses is None:
            database_socket_addresses = list()
            listen_port = config.getint("Database", "listen_port")
            notify_port = config.getint("Database", "notify_port")
            noftiy_hostname = config.get("Database", "notify_hostname")
            database_socket_addresses.append(
                SocketAddress(noftiy_hostname, notify_port, listen_port))

        FrontEndCommonConfigurationFunctions.__init__(self, hostname,
                                                      graph_label)

        self._executable_paths = executable_paths

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
        # TODO remove this self
        self._app_id = config.getint("Application", "appID")
        execute_data_spec_report = \
            config.getboolean("Reports", "writeTextSpecs")
        execute_partitioner_report = \
            config.getboolean("Reports", "writePartitionerReports")
        execute_placer_report = \
            config.getboolean("Reports", "writePlacerReports")
        execute_router_dat_based_report = \
            config.getboolean("Reports", "writeRouterDatReport")
        generate_performance_measurements = \
            config.getboolean("Reports", "outputTimesForSections")
        execute_router_report = \
            config.getboolean("Reports", "writeRouterReports")
        execute_write_reload_steps = \
            config.getboolean("Reports", "writeReloadSteps")
        generate_transciever_report = \
            config.getboolean("Reports", "writeTransceiverReport")
        execute_routing_info_report = \
            config.getboolean("Reports", "writeRouterInfoReport")
        generate_tag_report = \
            config.getboolean("Reports", "writeTagAllocationReports")
        in_debug_mode = config.get("Mode", "mode") == "Debug",
        create_database = config.getboolean("Database", "create_database")
        wait_on_confirmation = \
            config.getboolean("Database", "wait_on_confirmation")
        partitioner_algorithm = config.get("Partitioner", "algorithm")
        placer_algorithm = config.get("Placer", "algorithm")
        key_allocator_algorithm = config.get("KeyAllocator", "algorithm")
        router_algorithm = config.get("Routing", "algorithm")

        downed_chips = config.get("Machine", "down_chips")
        downed_cores = config.get("Machine", "down_cores")
        requires_virtual_board = config.getboolean("Machine", "virtual_board")
        self._machine_version = config.getint("Machine", "version")

        # sort out config None vs bool/int
        virtual_x_dimension = config.get("Machine", "virutal_board_x_dimension")
        virtual_y_dimension = config.get("Machine", "virutal_board_y_dimension")
        requires_wrap_around = config.get("Machine", "requires_wrap_arounds")
        if virtual_x_dimension != "None":
            virtual_x_dimension = int(virtual_x_dimension)
        if virtual_y_dimension != "None":
            virtual_y_dimension = int(virtual_y_dimension)
        if requires_wrap_around == "None":
            requires_wrap_around = False
        else:
            requires_wrap_around = \
                config.getboolean("Machine", "requires_wrap_arounds")

        # set up the configuration methods
        self._set_up_output_application_data_specifics(application_file_folder,
                                                       max_application_binaries)
        self._set_up_report_specifics(
            enabled_reports, write_text_spec, default_report_folder,
            max_reports_kept, write_provance)

        self._set_up_main_objects(
            app_id=self._app_id,
            execute_data_spec_report=execute_data_spec_report,
            execute_partitioner_report=execute_partitioner_report,
            execute_placer_report=execute_placer_report,
            execute_router_dat_based_report=execute_router_dat_based_report,
            execute_router_report=execute_router_report,
            execute_routing_info_report=execute_routing_info_report,
            execute_write_reload_steps=execute_write_reload_steps,
            generate_performance_measurements=generate_performance_measurements,
            generate_transciever_report=generate_transciever_report,
            in_debug_mode=in_debug_mode, reports_are_enabled=enabled_reports,
            generate_tag_report=generate_tag_report)

        self._set_up_pacman_algorthms_listings(
            partitioner_algorithm=partitioner_algorithm,
            placer_algorithm=placer_algorithm,
            key_allocator_algorithm=key_allocator_algorithm,
            routing_algorithm=router_algorithm)

        self._set_up_executable_specifics()

        # set up the interfaces with the machine
        FrontEndCommonInterfaceFunctions.__init__(
            self, self._reports_states, self._report_default_directory)
        self._setup_interfaces(
            downed_chips=downed_chips, downed_cores=downed_cores,
            hostname=hostname, machine_version=self._machine_version,
            requires_virtual_board=requires_virtual_board,
            requires_wrap_around=requires_wrap_around,
            virtual_x_dimension=virtual_x_dimension,
            virtual_y_dimension=virtual_y_dimension)

        if create_database:
            self._database_interface = DataBaseInterface(
                self._app_data_runtime_folder, wait_on_confirmation,
                database_socket_addresses)

        self._none_labelled_vertex_count = 0
        self._none_labelled_edge_count = 0
        self._time_scale_factor = 1

    def add_partitionable_vertex(self, vertex):
        """

        :param vertex
        :return:
        """
        # check that theres no partitioned vertices added so far
        if len(self._partitioned_graph.subvertices) > 0:
            raise exceptions.ConfigurationException(
                "The partitioned graph has already got some vertices, and "
                "therefore cannot be executed correctly. Please rectify and "
                "try again")
        self._partitionable_graph.add_vertex(vertex)

    def add_partitioned_vertex(self, vertex):
        """

        :param vertex
        :return:
        """
        # check that theres no partitioned vertices added so far
        if len(self._partitionable_graph.vertices) > 0:
            raise exceptions.ConfigurationException(
                "The partitionable graph has already got some vertices, and "
                "therefore cannot be executed correctly. Please rectify and "
                "try again")

        if self._partitioned_graph is None:
            self._partitioned_graph = PartitionedGraph(
                label="partitioned_graph for application id {}"
                .format(self._app_id))
        self._partitioned_graph.add_subvertex(vertex)

    def add_partitionable_edge(self, edge):
        """

        :param edge:
        :return:
        """
        self._partitionable_graph.add_edge(edge)

    def add_partitioned_edge(self, edge):
        """

        :param edge
        :return:
        """
        self._partitioned_graph.add_subedge(edge)

    def _set_runtime_in_time_steps_for_model(self, vertex, run_time):
        """

        :param vertex:
        :param run_time:
        :return:
        """
        self._no_machine_time_steps =\
            int((run_time * 1000.0) / vertex.machine_time_step)
        ceiled_machine_time_steps = math.ceil((run_time * 1000.0) /
                                              vertex.machine_time_step)
        if self._no_machine_time_steps != ceiled_machine_time_steps:
            raise exceptions.ConfigurationException(
                "The runtime and machine time step combination "
                "result in a factional number of machine runable "
                "time steps and therefore spinnaker cannot "
                "determine how many to run for")
        vertex.set_no_machine_time_steps(
            self._no_machine_time_steps)

    def run(self, run_time):
        """

        :param run_time:
        :return:
        """
        # create network report if needed
        if self._reports_states is not None:
            if len(self._partitionable_graph.vertices) > 0:
                reports.network_specification_partitionable_report(
                    self._report_default_directory, self._partitionable_graph,
                    self._hostname)
            else:
                reports.network_specification_report_partitioned_graph(
                    self._report_default_directory, self._partitioned_graph,
                    self._hostname)

        # calculate number of machine time steps
        if run_time is not None:
            for vertex in self._partitionable_graph.vertices:
                if isinstance(vertex, AbstractDataSpecableVertex):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
            for vertex in self._partitioned_graph.subvertices:
                if isinstance(vertex, AbstractPartitionedDataSpecableVertex):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
                elif isinstance(vertex, AbstractDataSpecableVertex):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
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
            logger.info("Time to map model: {}".format(timer.take_sample()))

        # execute data spec generation
        if do_timing:
            timer.start_timing()
        logger.info("*** Generating Output *** ")
        logger.debug("")
        executable_targets = self.generate_data_specifications()
        if do_timing:
            logger.info("Time to generate output: {}".format(
                timer.take_sample()))

        # execute data spec execution
        if do_timing:
            timer.start_timing()
        processor_to_app_data_base_address = \
            self.execute_data_specification_execution(
                config.getboolean("SpecExecution", "specExecOnHost"),
                self._hostname, self._placements, self._graph_mapper,
                self._writeTextSpecs, self._app_data_runtime_folder)

        if self._reports_states is not None:
            reports.write_memory_map_report(self._report_default_directory,
                                            processor_to_app_data_base_address)

        if do_timing:
            logger.info("Time to execute data specifications: {}".format(
                timer.take_sample()))

        if do_timing:
            timer.start_timing()

        logger.info("*** Loading tags ***")
        self._load_tags(self._tags)

        if self._do_load is True:
            logger.info("*** Loading data ***")
            self._load_application_data(
                self._placements, self._router_tables, self._graph_mapper,
                processor_to_app_data_base_address, self._hostname,
                self._app_id, self._app_data_runtime_folder,
                self._machine_version)
            logger.info("*** Loading executables ***")
            self._load_executable_images(executable_targets, self._app_id,
                                         self._app_data_runtime_folder)
        if do_timing:
            logger.info("Time to load: {}".format(timer.take_sample()))

        if self._do_run is True:
            logger.info("*** Running simulation... *** ")
            if self._reports_states.transciever_report:
                reports.re_load_script_running_aspects(
                    self._app_data_runtime_folder, executable_targets,
                    self._hostname, self._app_id, run_time)

                wait_on_confirmation = config.getboolean(
                    "Database", "wait_on_confirmation")
                send_start_notification = config.getboolean(
                    "Database", "send_start_notification")

                self._wait_for_cores_to_be_ready(executable_targets,
                                                 self._app_id)

                # wait till external app is ready for us to start if required
                if (self._database_interface is not None and
                        wait_on_confirmation):
                    logger.info(
                        "*** Awaiting for a response from an external source "
                        "to state its ready for the simulation to start ***")
                    self._database_interface.wait_for_confirmation()

                self._start_all_cores(executable_targets, self._app_id)

                if (self._database_interface is not None and
                        send_start_notification):
                    self._database_interface.send_start_notification()

                if self._runtime is None:
                    logger.info("Application is set to run forever - exiting")
                else:
                    self._wait_for_execution_to_complete(
                        executable_targets, self._app_id, self._runtime,
                        self._time_scale_factor)
                self._has_ran = True
                if self._retrieve_provance_data:

                    # retrieve provenance data
                    self._retieve_provance_data_from_machine(
                        executable_targets, self._router_tables, self._machine)
        elif isinstance(self._machine, VirtualMachine):
            logger.info(
                "*** Using a Virtual Machine so no simulation will occur")
        else:
            logger.info("*** No simulation requested: Stopping. ***")

    def map_model(self):
        """
        executes the pacman compilation stack
        """
        pacman_report_state = \
            self._reports_states.generate_pacman_report_states()

        # self._add_virtual_chips()

        # execute partitioner
        if len(self._partitionable_graph.vertices) > 0:
            self._execute_partitioner(pacman_report_state)

        # execute placer
        self._execute_placer(pacman_report_state)

        # exeucte tag allocator
        self._execute_tag_allocator(pacman_report_state)

        # execute key allocator
        self._execute_key_allocator(pacman_report_state)

        # execute router
        self._execute_router(pacman_report_state)

    def _execute_tag_allocator(self, pacman_report_state):
        """

        :param pacman_report_state:
        :return:
        """
        if self._tag_allocator_algorithm is None:
            self._tag_allocator_algorithm = BasicTagAllocator()
        else:
            self._tag_allocator_algorithm = self._tag_allocator_algorithm()

        # execute tag allocation
        self._tags = self._tag_allocator_algorithm.allocate_tags(
            self._machine, self._placements)

        # generate reports
        if (pacman_report_state is not None and
                pacman_report_state.tag_allocation_report):
            pacman_reports.tag_allocator_report(
                self._report_default_directory, self._tags)

    def _execute_key_allocator(self, pacman_report_state):
        """ executes the key allocator

        :param pacman_report_state:
        :return:
        """
        if self._key_allocator_algorithm is None:
            self._key_allocator_algorithm = BasicRoutingInfoAllocator()
        else:
            self._key_allocator_algorithm = self._key_allocator_algorithm()

        # Generate an n_keys map for the graph and add constraints
        n_keys_map = DictBasedPartitionedEdgeNKeysMap()
        if len(self._partitionable_graph.vertices) > 0:
            for edge in self._partitioned_graph.subedges:
                vertex_slice = self._graph_mapper.get_subvertex_slice(
                    edge.pre_subvertex)
                super_edge = self._graph_mapper\
                    .get_partitionable_edge_from_partitioned_edge(edge)

                if not isinstance(super_edge.pre_vertex,
                                  AbstractProvidesNKeysForEdge):
                    n_keys_map.\
                        set_n_keys_for_patitioned_edge(edge,
                                                       vertex_slice.n_atoms)
                else:
                    n_keys_map.set_n_keys_for_patitioned_edge(
                        edge,
                        super_edge.pre_vertex.get_n_keys_for_partitioned_edge(
                            edge, self._graph_mapper))

                if isinstance(super_edge.pre_vertex,
                              AbstractProvidesOutgoingEdgeConstraints):
                    edge.add_constraints(
                        super_edge.pre_vertex.get_outgoing_edge_constraints(
                            edge, self._graph_mapper))
                if isinstance(super_edge.post_vertex,
                              AbstractProvidesIncomingEdgeConstraints):
                    edge.add_constraints(
                        super_edge.post_vertex.get_incoming_edge_constraints(
                            edge, self._graph_mapper))
        else:
            for edge in self._partitioned_graph.subedges:
                if not isinstance(edge.pre_subvertex,
                                  AbstractProvidesNKeysForEdge):
                    n_keys_map.set_n_keys_for_patitioned_edge(edge, 1)
                else:
                    n_keys_map.set_n_keys_for_patitioned_edge(
                        edge,
                        edge.pre_subvertex.get_n_keys_for_partitioned_edge(
                            edge, self._graph_mapper))

                if isinstance(edge, AbstractProvidesNKeysForEdge):
                        n_keys = edge.\
                            get_n_keys_for_partitioned_edge(edge,
                                                            self._graph_mapper)
                        n_keys_map.set_n_keys_for_patitioned_edge(edge, n_keys)

                if isinstance(edge.pre_subvertex,
                              AbstractProvidesOutgoingEdgeConstraints):
                    edge.add_constraints(
                        edge.pre_subvertex.get_outgoing_edge_constraints(
                            edge, self._graph_mapper))
                if isinstance(edge.post_subvertex,
                              AbstractProvidesIncomingEdgeConstraints):
                    edge.add_constraints(
                        edge.post_subvertex.get_incoming_edge_constraints(
                            edge, self._graph_mapper))

        # execute routing info generator
        self._routing_infos = \
            self._key_allocator_algorithm.allocate_routing_info(
                self._partitioned_graph, self._placements, n_keys_map)

        # generate reports
        if (pacman_report_state is not None and
                pacman_report_state.routing_info_report):
            pacman_reports.routing_info_reports(
                self._report_default_directory, self._partitioned_graph,
                self._routing_infos)

    def _execute_router(self, pacman_report_state):
        """ exectes the router algorithum

        :param pacman_report_state:
        :return:
        """

        # set up a default placer algorithm if none are specified
        if self._router_algorithm is None:
            self._router_algorithm = BasicDijkstraRouting()
        else:
            self._router_algorithm = self._router_algorithm()

        self._router_tables = \
            self._router_algorithm.route(
                self._routing_infos, self._placements, self._machine,
                self._partitioned_graph)

        if pacman_report_state is not None and \
                pacman_report_state.router_report:
            pacman_reports.router_reports(
                graph=self._partitionable_graph, hostname=self._hostname,
                graph_to_sub_graph_mapper=self._graph_mapper,
                placements=self._placements,
                report_folder=self._report_default_directory,
                include_dat_based=pacman_report_state.router_dat_based_report,
                routing_tables=self._router_tables,
                routing_info=self._routing_infos, machine=self._machine)

        if self._in_debug_mode:

            # check that all routes are valid and no cycles exist
            valid_route_checker = ValidRouteChecker(
                placements=self._placements, routing_infos=self._routing_infos,
                routing_tables=self._router_tables, machine=self._machine,
                partitioned_graph=self._partitioned_graph)
            valid_route_checker.validate_routes()

    def _execute_partitioner(self, pacman_report_state):
        """ executes the partitioner function

        :param pacman_report_state:
        :return:
        """

        # execute partitioner or default partitioner (as seen fit)
        if self._partitioner_algorithm is None:
            self._partitioner_algorithm = BasicPartitioner()
        else:
            self._partitioner_algorithm = self._partitioner_algorithm()

        # execute partitioner
        self._partitioned_graph, self._graph_mapper = \
            self._partitioner_algorithm.partition(self._partitionable_graph,
                                                  self._machine)

        # execute reports
        if (pacman_report_state is not None and
                pacman_report_state.partitioner_report):
            pacman_reports.partitioner_reports(
                self._report_default_directory, self._hostname,
                self._partitionable_graph, self._graph_mapper)

    def _execute_placer(self, pacman_report_state):
        """ executes the placer

        :param pacman_report_state:
        :return:
        """

        # execute placer or default placer (as seen fit)
        if self._placer_algorithm is None:
            self._placer_algorithm = BasicPlacer()
        else:
            self._placer_algorithm = self._placer_algorithm()

        # execute placer
        self._placements = self._placer_algorithm.place(
            self._partitioned_graph, self._machine)

        # execute placer reports if needed
        if (pacman_report_state is not None and
                pacman_report_state.placer_report):
            pacman_reports.placer_reports_without_partitionable_graph(
                hostname=self._hostname, sub_graph=self._partitioned_graph,
                machine=self._machine, placements=self._placements,
                report_folder=self._report_default_directory)

    def generate_data_specifications(self):
        """ generates the dsg for the graph.

        :return:
        """

        # iterate though subvertexes and call generate_data_spec for each
        # vertex
        executable_targets = dict()
        no_processors = config.getint("Threading", "dsg_threads")
        thread_pool = ThreadPool(processes=no_processors)

        # create a progress bar for end users
        progress_bar = ProgressBar(len(list(self._placements.placements)),
                                   "Generating data specifications")
        data_generator_interfaces = list()
        for placement in self._placements.placements:
            binary_name = None
            if len(self._partitionable_graph.vertices) > 0:
                associated_vertex =\
                    self._graph_mapper.get_vertex_from_subvertex(
                        placement.subvertex)

                # if the vertex can generate a DSG, call it
                if isinstance(associated_vertex, AbstractDataSpecableVertex):

                    ip_tags = self._tags.get_ip_tags_for_vertex(
                        placement.subvertex)
                    reverse_ip_tags = self._tags.get_reverse_ip_tags_for_vertex(
                        placement.subvertex)
                    data_generator_interface = DataGeneratorInterface(
                        associated_vertex, placement.subvertex, placement,
                        self._partitioned_graph, self._partitionable_graph,
                        self._routing_infos, self._hostname,
                        self._graph_mapper, self._report_default_directory,
                        ip_tags, reverse_ip_tags, self._writeTextSpecs,
                        self._app_data_runtime_folder, progress_bar)
                    data_generator_interfaces.append(data_generator_interface)
                    thread_pool.apply_async(data_generator_interface.start)
                    binary_name = associated_vertex.get_binary_file_name()
            else:
                if isinstance(placement.subvertex,
                              AbstractPartitionedDataSpecableVertex):

                    ip_tags = self._tags.get_ip_tags_for_vertex(
                        placement.subvertex)
                    reverse_ip_tags = self._tags.get_reverse_ip_tags_for_vertex(
                        placement.subvertex)
                    data_generator_interface = DataSpecedGeneratorInterface(
                        placement.subvertex, placement,
                        self._partitioned_graph, self._routing_infos,
                        self._hostname, self._report_default_directory,
                        ip_tags, reverse_ip_tags, self._writeTextSpecs,
                        self._app_data_runtime_folder, progress_bar)
                    data_generator_interfaces.append(data_generator_interface)
                    thread_pool.apply_async(data_generator_interface.start)
                    binary_name = placement.subvertex.get_binary_file_name()
                else:
                    ip_tags = self._tags.get_ip_tags_for_vertex(
                        placement.subvertex)
                    reverse_ip_tags = self._tags.get_reverse_ip_tags_for_vertex(
                        placement.subvertex)
                    data_generator_interface = DataGeneratorInterface(
                        placement.subvertex, placement.subvertex, placement,
                        self._partitioned_graph, self._partitionable_graph,
                        self._routing_infos, self._hostname,
                        self._graph_mapper, self._report_default_directory,
                        ip_tags, reverse_ip_tags, self._writeTextSpecs,
                        self._app_data_runtime_folder, progress_bar)
                    data_generator_interfaces.append(data_generator_interface)
                    thread_pool.apply_async(data_generator_interface.start)
                    binary_name = placement.subvertex.get_binary_file_name()

            # Attempt to find this within search paths
            binary_path = \
                self._executable_paths.get_executable_path(binary_name)
            if binary_path is None:
                raise exceptions.ExecutableNotFoundException(binary_name)

            if binary_path in executable_targets:
                executable_targets[binary_path].add_processor(placement.x,
                                                              placement.y,
                                                              placement.p)
            else:
                processors = [placement.p]
                initial_core_subset = CoreSubset(placement.x, placement.y,
                                                 processors)
                list_of_core_subsets = [initial_core_subset]
                executable_targets[binary_path] = \
                    CoreSubsets(list_of_core_subsets)

        for data_generator_interface in data_generator_interfaces:
            data_generator_interface.wait_for_finish()
        thread_pool.close()
        thread_pool.join()

        # finish the progress bar
        progress_bar.end()

        return executable_targets

    def stop(self):
        """
        kills database if running
        :return:
        """

        if self._create_database:
            self._database_interface.stop()

        # stop the transciever
        self._txrx.close()

    def read_xml_file(self, file_path):
        """

        :param file_path:
        :return:
        """
        xml_interface = XMLInterface(file_path)
        self._partitionable_graph = xml_interface.read_in_file()

    def get_machine_dimensions(self):
        """
        method for end users to get the machine dimensions
        :return:
        """
        return {'x': self._machine.max_chip_x, 'y': self._machine.max_chip_y}

    # TODO THIS NEEDS REMOVING AND FIXING
    def host_based_data_specification_execution(
            self, hostname, placements, graph_mapper, write_text_specs,
            application_data_runtime_folder):
        """

        :param hostname:
        :param placements:
        :param graph_mapper:
        :param write_text_specs:
        :param application_data_runtime_folder:
        :return:
        """
        space_based_memory_tracker = dict()
        processor_to_app_data_base_address = dict()

        # create a progress bar for end users
        progress_bar = ProgressBar(len(list(placements.placements)),
                                   "Executing data specifications")

        for placement in placements.placements:
            if graph_mapper is not None:
                associated_vertex = graph_mapper.get_vertex_from_subvertex(
                    placement.subvertex)
            else:
                associated_vertex = placement.subvertex

            # if the vertex can generate a DSG, call it
            if (isinstance(associated_vertex, AbstractDataSpecableVertex) or
                isinstance(associated_vertex,
                           AbstractPartitionedDataSpecableVertex)):

                data_spec_file_path = \
                    associated_vertex.get_data_spec_file_path(
                        placement.x, placement.y, placement.p, hostname,
                        application_data_runtime_folder)
                app_data_file_path = \
                    associated_vertex.get_application_data_file_path(
                        placement.x, placement.y, placement.p, hostname,
                        application_data_runtime_folder)
                data_spec_reader = FileDataReader(data_spec_file_path)
                data_writer = FileDataWriter(app_data_file_path)

                # locate current memory requirement
                current_memory_available = SDRAM.DEFAULT_SDRAM_BYTES
                memory_tracker_key = (placement.x, placement.y)
                if memory_tracker_key in space_based_memory_tracker:
                    current_memory_available = space_based_memory_tracker[
                        memory_tracker_key]

                # generate a file writer for dse report (app pointer table)
                report_writer = None
                if write_text_specs:
                    new_report_directory = os.path.join(
                        self._report_default_directory, "data_spec_text_files")

                    if not os.path.exists(new_report_directory):
                        os.mkdir(new_report_directory)

                    file_name = "{}_DSE_report_for_{}_{}_{}.txt".format(
                        hostname, placement.x, placement.y, placement.p)
                    report_file_path = os.path.join(new_report_directory,
                                                    file_name)
                    report_writer = FileDataWriter(report_file_path)

                # generate data spec executor
                host_based_data_spec_executor = DataSpecificationExecutor(
                    data_spec_reader, data_writer, current_memory_available,
                    report_writer)

                # update memory calc and run data spec executor
                bytes_written_by_spec = None
                # noinspection PyBroadException
                try:
                    bytes_used_by_spec, bytes_written_by_spec = \
                        host_based_data_spec_executor.execute()
                except:
                    logger.error("Error executing data specification for {}"
                                 .format(associated_vertex))
                    traceback.print_exc()

                # update base address mapper
                processor_mapping_key = (placement.x, placement.y, placement.p)
                processor_to_app_data_base_address[processor_mapping_key] = {
                    'start_address':
                        ((SDRAM.DEFAULT_SDRAM_BYTES -
                          current_memory_available) +
                         constants.SDRAM_BASE_ADDR),
                    'memory_used': bytes_used_by_spec,
                    'memory_written': bytes_written_by_spec}

                space_based_memory_tracker[memory_tracker_key] = \
                    current_memory_available - bytes_used_by_spec

            # update the progress bar
            progress_bar.update()

        # close the progress bar
        progress_bar.end()
        return processor_to_app_data_base_address

    # TODO THIS NEEDS REMOVING AND FIXING
    def execute_data_specification_execution(
            self, host_based_execution, hostname, placements, graph_mapper,
            write_text_specs, runtime_application_data_folder):
        """

        :param host_based_execution:
        :param hostname:
        :param placements:
        :param graph_mapper:
        :param write_text_specs:
        :param runtime_application_data_folder:
        :return:
        """
        if host_based_execution:
            return self.host_based_data_specification_execution(
                hostname, placements, graph_mapper, write_text_specs,
                runtime_application_data_folder)
        else:
            return self._chip_based_data_specification_execution(hostname)

    # TODO THIS NEEDS REMOVING AND FIXING
    def _load_application_data(
            self, placements, router_tables, vertex_to_subvertex_mapper,
            processor_to_app_data_base_address, hostname, app_id,
            app_data_folder, machine_version):

        # if doing reload, start script
        if self._reports_states.transciever_report:
            reports.start_transceiver_rerun_script(
                app_data_folder, hostname, machine_version)

        # go through the placements and see if there's any application data to
        # load
        progress_bar = ProgressBar(len(list(placements.placements)),
                                   "Loading application data onto the machine")
        for placement in placements.placements:
            if vertex_to_subvertex_mapper is not None:
                associated_vertex = \
                    vertex_to_subvertex_mapper.get_vertex_from_subvertex(
                        placement.subvertex)
            else:
                associated_vertex = placement.subvertex

            if (isinstance(associated_vertex, AbstractDataSpecableVertex) or
                isinstance(associated_vertex,
                           AbstractPartitionedDataSpecableVertex)):
                logger.debug("loading application data for vertex {}"
                             .format(associated_vertex.label))
                key = (placement.x, placement.y, placement.p)
                start_address = \
                    processor_to_app_data_base_address[key]['start_address']
                memory_written = \
                    processor_to_app_data_base_address[key]['memory_written']
                file_path_for_application_data = \
                    associated_vertex.get_application_data_file_path(
                        placement.x, placement.y, placement.p, hostname,
                        app_data_folder)
                application_data_file_reader = SpinnmanFileDataReader(
                    file_path_for_application_data)
                logger.debug("writing application data for vertex {}"
                             .format(associated_vertex.label))
                self._txrx.write_memory(
                    placement.x, placement.y, start_address,
                    application_data_file_reader, memory_written)

                # update user 0 so that it points to the start of the
                # applications data region on sdram
                logger.debug("writing user 0 address for vertex {}"
                             .format(associated_vertex.label))
                user_o_register_address = \
                    self._txrx.get_user_0_register_address_from_core(
                        placement.x, placement.y, placement.p)
                self._txrx.write_memory(placement.x, placement.y,
                                        user_o_register_address, start_address)

                # add lines to rerun_script if requested
                if self._reports_states.transciever_report:
                    reports.re_load_script_application_data_load(
                        file_path_for_application_data, placement,
                        start_address, memory_written, user_o_register_address,
                        app_data_folder)
            progress_bar.update()
        progress_bar.end()

        progress_bar = ProgressBar(len(list(router_tables.routing_tables)),
                                   "Loading routing data onto the machine")

        # load each router table that is needed for the application to run into
        # the chips sdram
        for router_table in router_tables.routing_tables:
            if not self._machine.get_chip_at(router_table.x,
                                             router_table.y).virtual:
                self._txrx.clear_multicast_routes(router_table.x,
                                                  router_table.y)
                self._txrx.clear_router_diagnostic_counters(router_table.x,
                                                            router_table.y)

                if len(router_table.multicast_routing_entries) > 0:
                    self._txrx.load_multicast_routes(
                        router_table.x, router_table.y,
                        router_table.multicast_routing_entries, app_id=app_id)
                    if self._reports_states.transciever_report:
                        reports.re_load_script_load_routing_tables(
                            router_table, app_data_folder, app_id)
            progress_bar.update()
        progress_bar.end()