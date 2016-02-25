
# common front end imports
from pacman.operations.pacman_algorithm_executor import PACMANAlgorithmExecutor
from spinn_front_end_common.interface.spinnaker_main_interface import \
    SpinnakerMainInterface
from spinn_front_end_common.utilities import exceptions as exceptions
from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.abstract_models.abstract_data_specable_vertex \
    import AbstractDataSpecableVertex

# graph front end imports
from spinnaker_graph_front_end.abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex
from spinnaker_graph_front_end.utilities.xml_interface import XMLInterface
from spinnaker_graph_front_end.utilities.conf import config
from spinnaker_graph_front_end import extra_pacman_algorithms
from spinnaker_graph_front_end import _version

# general imports
import logging
import math
import os


logger = logging.getLogger(__name__)


class SpiNNaker(SpinnakerMainInterface):
    """
    Spinnaker
    """

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=None,
            extra_algorithms_for_auto_pause_and_resume=None):

        self._hostname = host_name

        extra_xml_path = list()
        extra_xml_path.append(
            os.path.join(os.path.dirname(extra_pacman_algorithms.__file__),
                         "spinnaker_graph_front_end_algorithms.xml"))

        SpinnakerMainInterface.__init__(
            self, config, _version, host_name=host_name,
            graph_label=graph_label, this_executable_finder=executable_finder,
            database_socket_addresses=database_socket_addresses,
            extra_algorithm_xml_paths=extra_xml_path,
            extra_algorithms_for_auto_pause_and_resume=
            extra_algorithms_for_auto_pause_and_resume)

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

    def  _create_algorithm_list(
            self, in_debug_mode, application_graph_changed, executing_reset,
            using_auto_pause_and_resume):

        algorithms = list()
        algorithms.append("SpiNNakerGraphFrontEndRuntimeUpdater")

        if application_graph_changed and not executing_reset:
            algorithms.append("FrontEndCommonEdgeToKeyMapper")

            if len(self._partitionable_graph.vertices) != 0:
                algorithms.append("FrontEndCommonEdgeToKeyMapper")
                algorithms.append("FrontEndCommonDatabaseWriter")
            else:
                algorithms.append("SpiNNakerGraphFrontEndDatabaseWriter")

        algorithms, optional_algorithms = \
            self._create_all_flows_algorithm_common(
                in_debug_mode, application_graph_changed, executing_reset,
                using_auto_pause_and_resume, algorithms)
        return algorithms, optional_algorithms

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

        pacman_executor = PACMANAlgorithmExecutor(
            algorithms=algorthims, inputs=inputs,
            xml_paths=xml_paths, required_outputs=required_outputs,
            optional_algorithms=list(),
            do_timings=config.getboolean("Reports", "outputTimesForSections"))
        pacman_executor = pacman_executor.execute_mapping()

        self._machine = pacman_executor.get_item("MemoryMachine")
        if not config.getboolean("Machine", "virtual_board"):
            self._txrx = pacman_executor.get_item("MemoryTransciever")

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}"\
            .format(self._hostname)
