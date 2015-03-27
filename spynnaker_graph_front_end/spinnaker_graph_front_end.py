"""
entrance class for the graph front end
"""
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

from spinn_front_end_common.interface.\
    front_end_common_configuration_functions import \
    FrontEndCommonConfigurationFunctions
from spinn_front_end_common.interface.\
    front_end_common_interface_functions import \
    FrontEndCommonInterfaceFunctions
from spinn_front_end_common.utilities import reports
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.utilities.timer import Timer
from spinnman.model.core_subset import CoreSubset
from spinnman.model.core_subsets import CoreSubsets
from spynnaker.pyNN.models.abstract_models.abstract_provides_incoming_edge_constraints import \
    AbstractProvidesIncomingEdgeConstraints
from spynnaker.pyNN.models.abstract_models.abstract_provides_n_keys_for_edge import \
    AbstractProvidesNKeysForEdge
from spynnaker.pyNN.models.abstract_models.abstract_provides_outgoing_edge_constraints import \
    AbstractProvidesOutgoingEdgeConstraints

from spynnaker_graph_front_end.DataSpecedGeneratorInterface import \
    DataSpecedGeneratorInterface
from spynnaker_graph_front_end.abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex

from spynnaker_graph_front_end.utilities.xml_interface import XMLInterface
from spynnaker_graph_front_end.utilities.conf import config

import logging
from multiprocessing.pool import ThreadPool


logger = logging.getLogger(__name__)


class SpiNNakerGraphFrontEnd(FrontEndCommonConfigurationFunctions,
                             FrontEndCommonInterfaceFunctions):
    """
    entrance class for the graph front end
    """

    def __init__(self, hostname=None, graph_label=None,
                 executable_paths=None):
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
        self._app_id = config.get("Application", "appID")
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
        partitioner_algorithm = config.get("Partitioner", "algorithm")
        placer_algorithm = config.get("Placer", "algorithm")
        key_allocator_algorithm = config.get("KeyAllocator", "algorithm")
        router_algorithm = config.get("Routing", "algorithm")
        virtual_x_dimension = \
            config.get("Machine", "virutal_board_x_dimension")
        virtual_y_dimension = \
            config.get("Machine", "virutal_board_y_dimension")
        downed_chips = config.get("Machine", "down_chips")
        downed_cores = config.get("Machine", "down_cores")
        requires_virtual_board = config.getboolean("Machine", "virtual_board")
        requires_wrap_around = config.get("Machine", "requires_wrap_arounds")
        # TODO get this bit fixed
        self._machine_version = config.getint("Machine", "version")
        # set up the configuration methods
        self._set_up_output_application_data_specifics(application_file_folder,
                                                       max_application_binaries)
        self._set_up_report_specifics(
            enabled_reports, write_text_spec, default_report_folder,
            max_reports_kept, write_provance)

        self._set_up_main_objects(
            app_id=self._app_id, create_database=create_database,
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

        self._none_labelled_vertex_count = 0
        self._none_labelled_edge_count = 0

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

    def run(self, run_time):
        """

        :param run_time:
        :return:
        """
        # create network report if needed
        if self._reports_states is not None:
            reports.network_specification_report(
                self._report_default_directory, self._partitionable_graph,
                self._hostname)

        # calculate number of machine time steps
        if run_time is not None:
            pass
            """
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
                        self._no_machine_time_steps)"""
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
                self._hostname, self._placements, self._graph_mapper,
                self._writeTextSpecs, self._app_data_runtime_folder)

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
                self._app_id, self._app_data_runtime_folder,
                self._machine_version)
            logger.info("*** Loading executables ***")
            self._load_executable_images(executable_targets, self._app_id,
                                         self._app_data_runtime_folder)
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
                super_edge = \
                    self._graph_mapper\
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
                                   "on generating data specifications")
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
                        ip_tags, reverse_ip_tags, progress_bar)
                    data_generator_interfaces.append(data_generator_interface)
                    thread_pool.apply_async(data_generator_interface.start)
                    binary_name = associated_vertex.get_binary_file_name()
            else:
                if isinstance(placement.subvertex, AbstractPartitionedDataSpecableVertex):
                    ip_tags = self._tags.get_ip_tags_for_vertex(
                        placement.subvertex)
                    reverse_ip_tags = self._tags.get_reverse_ip_tags_for_vertex(
                        placement.subvertex)
                    data_generator_interface = DataSpecedGeneratorInterface(
                        placement.subvertex, placement,
                        self._partitioned_graph, self._routing_infos,
                        self._hostname, self._report_default_directory,
                        ip_tags, reverse_ip_tags, progress_bar
                    )
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

    def stop(self, stop_on_board=True):
        """

        :param stop_on_board:
        :return:
        """
        if stop_on_board:
            for router_table in self._router_tables.routing_tables:
                if (not self._machine.get_chip_at(router_table.x,
                                                  router_table.y).virtual and
                        len(router_table.multicast_routing_entries) > 0):
                    self._txrx.clear_router_diagnostic_counters(router_table.x,
                                                                router_table.y)
            for ip_tag in self._tags.ip_tags:
                self._txrx.clear_ip_tag(
                    ip_tag.tag, board_address=ip_tag.board_address)
            for reverse_ip_tag in self._tags.reverse_ip_tags:
                self._txrx.clear_ip_tag(
                    reverse_ip_tag.tag,
                    board_address=reverse_ip_tag.board_address)

            # self._txrx.stop_application(self._app_id)
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
