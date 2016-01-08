
# pacman imports
from pacman.model.partitionable_graph.partitionable_graph import \
    PartitionableGraph
from pacman.model.partitioned_graph.partitioned_graph import PartitionedGraph
from pacman.operations import algorithm_reports as pacman_algorithm_reports

# common front end imports
from spinn_front_end_common.utilities import exceptions as exceptions
from spinn_front_end_common.utilities.report_states import ReportState
from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.abstract_models.abstract_data_specable_vertex \
    import AbstractDataSpecableVertex

# graph front end imports
from abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex
from utilities.xml_interface import XMLInterface
from utilities.conf import config
import extra_pacman_algorithms

# general imports
import logging
import math
import os


logger = logging.getLogger(__name__)


class SpiNNakerGraphFrontEnd(object):
    """
    Spinnaker
    """

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=None, algorithms=None,
            partitioner_algorithm=None):

        self._hostname = host_name

        # mapping overloads
        self._overloaded_partitioner_algorithm = partitioner_algorithm
        self._overloaded_algortihms = algorithms

        # update graph label if needed
        if graph_label is None:
            graph_label = "Application_graph"

        # pacman objects
        self._partitionable_graph = PartitionableGraph(label=graph_label)
        self._partitioned_graph = PartitionedGraph(label=graph_label)
        self._graph_mapper = None
        self._placements = None
        self._router_tables = None
        self._routing_infos = None
        self._tags = None
        self._machine = None
        self._txrx = None
        self._has_ran = False
        self._reports_states = None
        self._app_id = None
        self._runtime = None
        self._current_run_ms = None
        self._buffer_manager = None

        # holders for data needed for reset when nothing changes in the
        # application graph
        self._processor_to_app_data_base_address_mapper = None
        self._vertex_to_app_data_file_paths = None

        # database objects
        self._database_socket_addresses = set()
        if database_socket_addresses is not None:
            self._database_socket_addresses.union(database_socket_addresses)

        self._database_interface = None
        self._create_database = None

        # Determine default executable folder location
        # and add this default to end of list of search paths
        self._executable_finder = executable_finder

        # population holders
        self._none_labelled_vertex_count = 0
        self._none_labelled_edge_count = 0

        # holder for number of times the timer event should exuecte for the sim
        self._no_machine_time_steps = None
        self._machine_time_step = None
        self._no_sync_changes = 0

        # holder for the exeuctable targets (which we will need for reset and
        # pause and resume functionality
        self._executable_targets = None

        # state thats needed the first time around
        if self._app_id is None:
            self._app_id = config.getint("Machine", "appID")

            if config.getboolean("Reports", "reportsEnabled"):
                self._reports_states = ReportState(
                    config.getboolean("Reports", "writePartitionerReports"),
                    config.getboolean("Reports",
                                      "writePlacerReportWithPartitionable"),
                    config.getboolean("Reports",
                                      "writePlacerReportWithoutPartitionable"),
                    config.getboolean("Reports", "writeRouterReports"),
                    config.getboolean("Reports", "writeRouterInfoReport"),
                    config.getboolean("Reports", "writeTextSpecs"),
                    config.getboolean("Reports", "writeReloadSteps"),
                    config.getboolean("Reports", "writeTransceiverReport"),
                    config.getboolean("Reports", "outputTimesForSections"),
                    config.getboolean("Reports", "writeTagAllocationReports"))

            # set up reports default folder
            self._report_default_directory, this_run_time_string = \
                helpful_functions.set_up_report_specifics(
                    default_report_file_path=config.get(
                        "Reports", "defaultReportFilePath"),
                    max_reports_kept=config.getint(
                        "Reports", "max_reports_kept"),
                    app_id=self._app_id)

            # set up application report folder
            self._app_data_runtime_folder = \
                helpful_functions.set_up_output_application_data_specifics(
                    max_application_binaries_kept=config.getint(
                        "Reports", "max_application_binaries_kept"),
                    where_to_write_application_data_files=config.get(
                        "Reports", "defaultApplicationDataFilePath"),
                    app_id=self._app_id,
                    this_run_time_string=this_run_time_string)

        # set up machine targetted data
        self._set_up_machine_specifics(host_name)

        self._time_scale_factor = 1
        logger.info("Setting time scale factor to {}."
                    .format(self._time_scale_factor))

        logger.info("Setting appID to %d." % self._app_id)

        # get the machine time step
        logger.info("Setting machine time step to {} micro-seconds."
                    .format(self._machine_time_step))

    def _set_up_machine_specifics(self, hostname):
        self._machine_time_step = config.getint("Machine", "machineTimeStep")

        if hostname is not None:
            self._hostname = hostname
            logger.warn("The machine name from PYNN setup is overriding the "
                        "machine name defined in the spynnaker.cfg file")
        elif config.has_option("Machine", "machineName"):
            self._hostname = config.get("Machine", "machineName")
        else:
            raise Exception("A SpiNNaker machine must be specified in "
                            "spynnaker.cfg.")
        use_virtual_board = config.getboolean("Machine", "virtual_board")
        if self._hostname == 'None' and not use_virtual_board:
            raise Exception("A SpiNNaker machine must be specified in "
                            "spynnaker.cfg.")

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

    def add_partitionable_edge(self, edge, partition_id=None):
        """

        :param edge:
        :return:
        """
        self._partitionable_graph.add_edge(edge, partition_id)

    def add_partitioned_edge(self, edge, partition_id=None):
        """

        :param edge
        :return:
        """
        self._partitioned_graph.add_subedge(edge, partition_id)

    def run(self, run_time):
        """

        :param run_time:
        :return:
        """

        # calculate number of machine time steps
        total_run_time = self._calculate_number_of_machine_time_steps(run_time)
        self._current_run_ms = run_time
        self._runtime = run_time

        inputs = self._create_pacman_executor_inputs(total_run_time)
        required_outputs = self._create_pacman_executor_outputs()
        algorithms = self._create_algorithm_list(
            config.get("Mode", "mode") == "Debug")
        xml_paths = self._create_xml_paths()

        pacman_exeuctor = helpful_functions.do_mapping(
            inputs, algorithms, required_outputs, xml_paths,
            config.getboolean("Reports", "outputTimesForSections"))

        # gather provenance data from the executor itself if needed
        if config.get("Reports", "writeProvanceData"):
            pacman_executor_file_path = os.path.join(
                pacman_exeuctor.get_item("ProvenanceFilePath"),
                "PACMAN_provancence_data.xml")
            pacman_exeuctor.write_provenance_data_in_xml(
                pacman_executor_file_path,
                pacman_exeuctor.get_item("MemoryTransciever"))

        # sort out outputs datas
        self._txrx = pacman_exeuctor.get_item("MemoryTransciever")
        self._placements = pacman_exeuctor.get_item("MemoryPlacements")
        self._router_tables = pacman_exeuctor.get_item("MemoryRoutingTables")
        self._routing_infos = pacman_exeuctor.get_item("MemoryRoutingInfos")
        self._tags = pacman_exeuctor.get_item("MemoryTags")
        if len(self._partitionable_graph.vertices) != 0:
            self._graph_mapper = pacman_exeuctor.get_item("MemoryGraphMapper")
        self._partitioned_graph = \
            pacman_exeuctor.get_item("MemoryPartitionedGraph")
        self._machine = pacman_exeuctor.get_item("MemoryMachine")
        self._database_interface = pacman_exeuctor.get_item(
            "DatabaseInterface")
        self._has_ran = pacman_exeuctor.get_item("RanToken")

        # reset the reset flag to say the last thing was not a reset call
        self._current_run_ms = total_run_time

    @staticmethod
    def _create_xml_paths():
        # add the extra xml files from the cfg file
        xml_paths = config.get("Mapping", "extra_xmls_paths")
        if xml_paths == "None":
            xml_paths = list()
        else:
            xml_paths = xml_paths.split(",")

        xml_paths.append(
            os.path.join(os.path.dirname(extra_pacman_algorithms.__file__),
                         "spinnaker_graph_front_end_algorithms.xml"))
        xml_paths.append(os.path.join(os.path.dirname(
            pacman_algorithm_reports.__file__), "reports_metadata.xml"))

        return xml_paths

    def _create_algorithm_list(self, in_debug_mode):
        if self._overloaded_algortihms is None:
            algorithms = list()

            algorithm_names = \
                config.get("Mapping", "algorithms") + "," + \
                config.get("Mapping", "interface_algorithms")

            algorithm_strings = algorithm_names.split(",")
            for algorithm_string in algorithm_strings:
                split_string = algorithm_string.split(":")
                if len(split_string) == 1:
                    algorithms.append(split_string[0])
                else:
                    raise exceptions.ConfigurationException(
                        "The tool chain expects config params of list of 1 "
                        "element with ,. Where the elements are either: the "
                        "algorithum_name:algorithm_config_file_path, or "
                        "algorithum_name if its a interal to pacman algorithm."
                        " Please rectify this and try again")

            contains_a_partitionable_graph = \
                len(self._partitionable_graph.vertices) > 0

            # if using virutal machine, add to list of algorithms the virtual
            # machine generator, otherwise add the standard machine generator
            if config.getboolean("Machine", "virtual_board"):
                algorithms.append("FrontEndCommonVirtualMachineInterfacer")
            else:
                if self._machine is None and self._txrx is None:
                    algorithms.append("FrontEndCommonMachineInterfacer")
                algorithms.append("FrontEndCommonApplicationRunner")

                # if going to write provanence data after the run add the two
                # provenance gatherers
                if config.get("Reports", "writeProvanceData"):
                    algorithms.append("FrontEndCommonProvenanceGatherer")

                # if the end user wants reload script, add the reload script
                # creator to the list
                if config.getboolean("Reports", "writeReloadSteps"):
                    algorithms.append("FrontEndCommonReloadScriptCreator")

            if config.getboolean("Reports", "writeMemoryMapReport"):
                algorithms.append("FrontEndCommonMemoryMapReport")

            if config.getboolean("Reports", "writeNetworkSpecificationReport")\
                    and contains_a_partitionable_graph:
                algorithms.append(
                    "FrontEndCommonNetworkSpecificationPartitionableReport")

            # define mapping between output types and reports
            if self._reports_states is not None \
                    and self._reports_states.tag_allocation_report:
                algorithms.append("TagReport")
            if self._reports_states is not None \
                    and self._reports_states.routing_info_report:
                algorithms.append("routingInfoReports")
            if self._reports_states is not None \
                    and self._reports_states.router_report:
                algorithms.append("RouterReports")
            if self._reports_states is not None \
                    and self._reports_states.partitioner_report\
                    and contains_a_partitionable_graph:
                algorithms.append("PartitionerReport")
            if (self._reports_states is not None and
                    self._reports_states.
                    placer_report_with_partitionable_graph and
                    contains_a_partitionable_graph):
                algorithms.append("PlacerReportWithPartitionableGraph")
            if (self._reports_states is not None and
                    self._reports_states.
                    placer_report_without_partitionable_graph):
                algorithms.append("PlacerReportWithoutPartitionableGraph")
            # add debug algorithms if needed
            if in_debug_mode:
                algorithms.append("ValidRoutesChecker")

            # add partitioner algorithm if the partitionable graph has more
            # than 0 entries
            if contains_a_partitionable_graph:
                algorithms.append("{}".format(
                    config.get("Mapping", "partitionerAlgorithm")))
                algorithms.append("MallocBasedChipIDAllocator")

                algorithms.append(
                    "SpinnakerGraphFrontEndPartitionableGraphEdgeToKeyMapper")
                algorithms.append(
                    "FrontEndCommonPartitionableGraphHost"
                    "ExecuteDataSpecification")
                algorithms.append(
                    "FrontEndCommomPartitionableGraphDataSpecificationWriter")
                algorithms.append("FrontEndCommonDatabaseWriter")
            else:
                algorithms.append("MallocBasedPartitionedChipIDAllocator")
                algorithms.append(
                    "SpinnakerGraphFrontEndPartitionedGraphEdgeToKeyMapper")
                algorithms.append(
                    "SpinnakerGraphFrontEndPartitionedGraphData"
                    "SpecificationWriter")
                algorithms.append("FrontEndCommonNotificationProtocol")
                algorithms.append(
                    "SpinnakerGraphFrontEndPartitionedGraphHost"
                    "BasedDataSpecificationExeuctor")
                algorithms.append("SpiNNakerGraphFrontEndDatabaseWriter")
            # application data loader is agnostic to graph
            algorithms.append(
                "FrontEndCommonPartitionableGraphApplicationDataLoader")

            return algorithms
        else:
            if self._overloaded_partitioner_algorithm is None:
                return self._overloaded_algortihms
            else:
                algorithums = "{},{}".format(
                    self._overloaded_partitioner_algorithm,
                    self._overloaded_algortihms)
                return algorithums

    @staticmethod
    def _create_pacman_executor_outputs():
        # explicitly define what outputs the graph front end expects
        required_outputs = list()
        if config.getboolean("Machine", "virtual_board"):
            required_outputs.extend([
                "MemoryPlacements", "MemoryRoutingTables",
                "MemoryRoutingInfos", "MemoryTags", "MemoryPartitionedGraph",
                "MemoryGraphMapper"])
        else:
            required_outputs.append("RanToken")
        # if front end wants reload script, add requires reload token
        if config.getboolean("Reports", "writeReloadSteps"):
            required_outputs.append("ReloadToken")
        return required_outputs

    def _create_pacman_executor_inputs(self, total_runtime):
        application_graph_changed = True
        inputs = list()

        # file path to store any provenance data to
        provenance_file_path = \
            os.path.join(self._report_default_directory, "provance_data")
        if not os.path.exists(provenance_file_path):
                os.mkdir(provenance_file_path)

        # all modes need the NoSyncChanges
        if application_graph_changed:
            self._no_sync_changes = 0
        inputs.append(
            {'type': "NoSyncChanges", 'value': self._no_sync_changes})

        # support resetting the machine during start up
        if (config.getboolean("Machine", "reset_machine_on_startup") and
                not self._has_ran):
            inputs.append(
                {"type": "ResetMachineOnStartupFlag", 'value': True})
        else:
            inputs.append(
                {"type": "ResetMachineOnStartupFlag", 'value': False})

        if self._txrx is not None:
            inputs.append({"type": "MemoryTransciever", 'value': self._txrx})

        if self._machine is not None:
            inputs.append({"type": "MemoryMachine", 'value': self._machine})

        # support runtime updater
        if self._has_ran:
            no_machine_time_steps =\
                int(((total_runtime - self._current_run_ms) * 1000.0) /
                    self._machine_time_step)
            inputs.append({'type': "RunTimeMachineTimeSteps",
                           'value': no_machine_time_steps})

        # FrontEndCommonPartitionableGraphApplicationDataLoader after a
        # reset and no changes
        if not self._has_ran and not application_graph_changed:
            inputs.append(({
                'type': "ProcessorToAppDataBaseAddress",
                "value": self._processor_to_app_data_base_address_mapper}))
            inputs.append({"type": "VertexToAppDataFilePaths",
                           'value': self._vertex_to_app_data_file_paths})
            inputs.append({'type': "WriteCheckerFlag",
                           'value': config.getboolean(
                               "Mode", "verify_writes")})

        # the application graph has changed, so new binaries are being
        # loaded and therefore sync mode starts at zero again.
        self._no_sync_changes = 0

        # make a folder for the json files to be stored in
        json_folder = os.path.join(
            self._report_default_directory, "json_files")
        if not os.path.exists(json_folder):
            os.mkdir(json_folder)

        # translate config "None" to None
        width = config.get("Machine", "width")
        height = config.get("Machine", "height")
        if width == "None":
            width = None
        else:
            width = int(width)
        if height == "None":
            height = None
        else:
            height = int(height)

        number_of_boards = config.get("Machine", "number_of_boards")
        if number_of_boards == "None":
            number_of_boards = None

        scamp_socket_addresses = config.get("Machine",
                                            "scamp_connections_data")
        if scamp_socket_addresses == "None":
            scamp_socket_addresses = None

        boot_port_num = config.get("Machine", "boot_connection_port_num")
        if boot_port_num == "None":
            boot_port_num = None
        else:
            boot_port_num = int(boot_port_num)

        if len(self.partitionable_graph.vertices) > 0:
            inputs.append({'type': "MemoryPartitionableGraph",
                           'value': self._partitionable_graph})
        if len(self.partitioned_graph.subvertices) > 0:
            inputs.append({'type': "MemoryPartitionedGraph",
                           'value': self._partitioned_graph})

        inputs.append({'type': 'ReportFolder',
                       'value': self._report_default_directory})
        inputs.append({'type': "ApplicationDataFolder",
                       'value': self._app_data_runtime_folder})
        inputs.append({'type': 'IPAddress', 'value': self._hostname})

        # basic input stuff
        inputs.append({'type': "BMPDetails",
                       'value': config.get("Machine", "bmp_names")})
        inputs.append({'type': "DownedChipsDetails",
                       'value': config.get("Machine", "down_chips")})
        inputs.append({'type': "DownedCoresDetails",
                       'value': config.get("Machine", "down_cores")})
        inputs.append({'type': "BoardVersion",
                       'value': config.getint("Machine", "version")})
        inputs.append({'type': "NumberOfBoards",
                       'value': number_of_boards})
        inputs.append({'type': "MachineWidth", 'value': width})
        inputs.append({'type': "MachineHeight", 'value': height})
        inputs.append({'type': "AutoDetectBMPFlag",
                       'value': config.getboolean("Machine",
                                                  "auto_detect_bmp")})
        inputs.append({'type': "EnableReinjectionFlag",
                       'value': config.getboolean("Machine",
                                                  "enable_reinjection")})
        inputs.append({'type': "ScampConnectionData",
                       'value': scamp_socket_addresses})
        inputs.append({'type': "BootPortNum", 'value': boot_port_num})
        inputs.append({'type': "APPID", 'value': self._app_id})
        inputs.append({'type': "RunTime", 'value': self._current_run_ms})
        inputs.append({'type': "TimeScaleFactor",
                       'value': self._time_scale_factor})
        inputs.append({'type': "MachineTimeStep",
                       'value': self._machine_time_step})
        inputs.append({'type': "DatabaseSocketAddresses",
                       'value': self._database_socket_addresses})
        inputs.append({'type': "DatabaseWaitOnConfirmationFlag",
                       'value': config.getboolean(
                           "Database", "wait_on_confirmation")})
        inputs.append({'type': "WriteCheckerFlag",
                       'value': config.getboolean(
                           "Mode", "verify_writes")})
        inputs.append({'type': "WriteTextSpecsFlag",
                       'value': config.getboolean(
                           "Reports", "writeTextSpecs")})
        inputs.append({'type': "ExecutableFinder",
                       'value': self._executable_finder})
        inputs.append({'type': "MachineHasWrapAroundsFlag",
                       'value': config.getboolean(
                           "Machine", "requires_wrap_arounds")})
        inputs.append({'type': "ReportStates",
                       'value': self._reports_states})
        inputs.append({'type': "UserCreateDatabaseFlag",
                       'value': config.get("Database", "create_database")})
        inputs.append(
            {'type': "ExecuteMapping",
             'value': config.getboolean(
                 "Database", "create_routing_info_to_atom_id_mapping")})
        inputs.append({'type': "DatabaseSocketAddresses",
                       'value': self._database_socket_addresses})
        inputs.append({'type': "SendStartNotifications",
                       'value': config.getboolean(
                           "Database", "send_start_notification")})
        inputs.append({'type': "ProvenanceFilePath",
                       'value': provenance_file_path})

        # add paths for each file based version
        inputs.append({'type': "FileCoreAllocationsFilePath",
                       'value': os.path.join(
                           json_folder, "core_allocations.json")})
        inputs.append({'type': "FileSDRAMAllocationsFilePath",
                       'value': os.path.join(
                           json_folder, "sdram_allocations.json")})
        inputs.append({'type': "FileMachineFilePath",
                       'value': os.path.join(
                           json_folder, "machine.json")})
        inputs.append({'type': "FilePartitionedGraphFilePath",
                       'value': os.path.join(
                           json_folder, "partitioned_graph.json")})
        inputs.append({'type': "FilePlacementFilePath",
                       'value': os.path.join(
                           json_folder, "placements.json")})
        inputs.append({'type': "FileRouingPathsFilePath",
                       'value': os.path.join(
                           json_folder, "routing_paths.json")})
        inputs.append({'type': "FileConstraintsFilePath",
                       'value': os.path.join(
                           json_folder, "constraints.json")})

        if self._has_ran:
            logger.warn(
                "The graph has changed since the original graph was loaded "
                "and ran. Therefore decisions made during the mapping "
                "process will be incorrect now, and therefore mapping "
                "needs to be redone. Sorry. Please note that any "
                "recorded data will also have been lost. If you were "
                "wanting this data, please rerun your script and extract"
                "the data before recalling run. Thank you")

        return inputs

    def _calculate_number_of_machine_time_steps(self, run_time):
        if run_time is not None:
            if self._current_run_ms is not None:
                run_time += self._current_run_ms
            for vertex in self._partitionable_graph.vertices:
                if isinstance(vertex, AbstractDataSpecableVertex):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
            for vertex in self._partitioned_graph.subvertices:
                if (isinstance(
                        vertex, AbstractPartitionedDataSpecableVertex) or
                        isinstance(vertex, AbstractDataSpecableVertex)):
                    self._set_runtime_in_time_steps_for_model(vertex, run_time)
        else:
            self._no_machine_time_steps = None
            logger.warn("You have set a runtime that will never end, this may"
                        "cause the neural models to fail to partition "
                        "correctly")
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
            raise exceptions.ConfigurationException(
                "The runtime and machine time step combination "
                "result in a fractional number of machine runnable "
                "time steps and therefore spinnaker cannot "
                "determine how many to run for")
        vertex.set_no_machine_time_steps(self._no_machine_time_steps)

    def read_partitionable_graph_xml_file(self, file_path):
        """

        :param file_path:
        :return:
        """
        xml_interface = XMLInterface(file_path)
        self._partitionable_graph = xml_interface.read_in_file()

    def read_partitioned_graph_xml_file(self, file_path):
        """

        :param file_path:
        :return:
        """
        xml_interface = XMLInterface(file_path)
        self._partitioned_graph = xml_interface.read_in_file()

    def get_machine_dimensions(self):
        """ Get the machine dimensions
        :return:
        """
        if self._machine is None:
            self._run_algorithms_for_machine_gain()

        return {'x': self._machine.max_chip_x, 'y': self._machine.max_chip_y}

    def _run_algorithms_for_machine_gain(self):
        inputs = self._create_pacman_executor_inputs(self._current_run_ms)
        algorthims = list()
        if config.getboolean("Machine", "virtual_board"):
            algorthims.append("FrontEndCommonVirtualMachineInterfacer")
        else:
            algorthims.append("FrontEndCommonMachineInterfacer")
        required_outputs = list()
        required_outputs.append("MemoryMachine")
        xml_paths = list()

        pacman_exeuctor = helpful_functions.do_mapping(
            inputs, algorthims, required_outputs, xml_paths,
            config.getboolean("Reports", "outputTimesForSections"))

        self._machine = pacman_exeuctor.get_item("MemoryMachine")
        if not config.getboolean("Machine", "virtual_board"):
            self._txrx = pacman_exeuctor.get_item("MemoryTransciever")

    @property
    def app_id(self):
        """

        :return:
        """
        return self._app_id

    @property
    def has_ran(self):
        """

        :return:
        """
        return self._has_ran

    @property
    def machine_time_step(self):
        """

        :return:
        """
        return self._machine_time_step

    @property
    def no_machine_time_steps(self):
        """

        :return:
        """
        return self._no_machine_time_steps

    @property
    def timescale_factor(self):
        """

        :return:
        """
        return self._time_scale_factor

    @property
    def partitioned_graph(self):
        """

        :return:
        """
        return self._partitioned_graph

    @property
    def partitionable_graph(self):
        """

        :return:
        """
        return self._partitionable_graph

    @property
    def placements(self):
        """

        :return:
        """
        return self._placements

    @property
    def transceiver(self):
        """

        :return:
        """
        return self._txrx

    @property
    def graph_mapper(self):
        """

        :return:
        """
        return self._graph_mapper

    @property
    def routing_infos(self):
        """

        :return:
        """
        return self._routing_infos

    def set_app_id(self, value):
        """

        :param value:
        :return:
        """
        self._app_id = value

    def get_current_time(self):
        """

        :return:
        """
        if self._has_ran:
            return float(self._runtime)
        return 0.0

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}"\
            .format(self._hostname)

    def stop(self, turn_off_machine=None, clear_routing_tables=None,
             clear_tags=None):
        """
        :param turn_off_machine: decides if the machine should be powered down\
            after running the execution. Note that this powers down all boards\
            connected to the BMP connections given to the transceiver
        :type turn_off_machine: bool
        :param clear_routing_tables: informs the tool chain if it\
            should turn off the clearing of the routing tables
        :type clear_routing_tables: bool
        :param clear_tags: informs the tool chain if it should clear the tags\
            off the machine at stop
        :type clear_tags: boolean
        :return: None
        """

        # if not a virtual machine, then shut down stuff on the board
        if not config.getboolean("Machine", "virtual_board"):

            if turn_off_machine is None:
                turn_off_machine = \
                    config.getboolean("Machine", "turn_off_machine")

            if clear_routing_tables is None:
                clear_routing_tables = config.getboolean(
                    "Machine", "clear_routing_tables")

            if clear_tags is None:
                clear_tags = config.getboolean("Machine", "clear_tags")

            # if stopping on machine, clear iptags and
            if clear_tags:
                for ip_tag in self._tags.ip_tags:
                    self._txrx.clear_ip_tag(
                        ip_tag.tag, board_address=ip_tag.board_address)
                for reverse_ip_tag in self._tags.reverse_ip_tags:
                    self._txrx.clear_ip_tag(
                        reverse_ip_tag.tag,
                        board_address=reverse_ip_tag.board_address)

            # if clearing routing table entries, clear
            if clear_routing_tables:
                for router_table in self._router_tables.routing_tables:
                    if not self._machine.get_chip_at(router_table.x,
                                                     router_table.y).virtual:
                        self._txrx.clear_multicast_routes(router_table.x,
                                                          router_table.y)

            # execute app stop
            self._txrx.stop_application(self._app_id)

            # close database
            if self._create_database:
                self._database_interface.stop()

            # stop the transceiver
            if turn_off_machine:
                logger.info("Turning off machine")
            self._txrx.close(power_off_machine=turn_off_machine)

    def _add_socket_address(self, socket_address):
        """

        :param socket_address:
        :return:
        """
        self._database_socket_addresses.add(socket_address)
