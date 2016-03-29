
# pacman imports
from pacman.operations.pacman_algorithm_executor import PACMANAlgorithmExecutor

# common front end imports
from spinn_front_end_common.interface.spinnaker_main_interface import \
    SpinnakerMainInterface
from spinn_front_end_common.interface import interface_functions

# graph front end imports
from spinnaker_graph_front_end.utilities.xml_interface import XMLInterface
from spinnaker_graph_front_end.utilities.conf import config
from spinnaker_graph_front_end import _version

# general imports
import logging
import os


logger = logging.getLogger(__name__)


class SpiNNaker(SpinnakerMainInterface):

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=None, dsg_algorithm=None):

        # dsg algorithm store for user defined algorithms
        self._user_dsg_algorithm = dsg_algorithm

        # create xml path for where to locate GFE related functions when
        # using auto pause and resume
        extra_xml_path = list()

        # create list of extra algorithms for auto pause and resume
        extra_mapping_inputs = dict()
        extra_mapping_algorithms = list()
        extra_pre_run_algorithms = list()
        extra_post_run_algorithms = list()

        extra_mapping_inputs["ExecuteMapping"] = config.getboolean(
            "Database", "create_routing_info_to_atom_id_mapping")

        SpinnakerMainInterface.__init__(
            self, config, _version, host_name=host_name,
            graph_label=graph_label, this_executable_finder=executable_finder,
            database_socket_addresses=database_socket_addresses,
            extra_algorithm_xml_paths=extra_xml_path,
            extra_mapping_inputs=extra_mapping_inputs,
            extra_mapping_algorithms=extra_mapping_algorithms,
            extra_pre_run_algorithms=extra_pre_run_algorithms,
            extra_post_run_algorithms=extra_post_run_algorithms)

        # set up machine targeted data
        self._machine_time_step = config.getint("Machine", "machineTimeStep")
        self.set_up_machine_specifics(host_name)

        self._time_scale_factor = 1
        logger.info("Setting time scale factor to {}."
                    .format(self._time_scale_factor))

        logger.info("Setting appID to %d." % self._app_id)

        # get the machine time step
        logger.info("Setting machine time step to {} micro-seconds."
                    .format(self._machine_time_step))

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

    def generate_file_machine(self):
        """
        supports user which need to know the machine for external usages
        before running the main tools.
        :return:
        """
        if self._machine is None:
            self._run_algorithms_for_machine_gain(["FileMachine"])
        else:
            self._use_machine_to_generate_file_machine()

    def _use_machine_to_generate_file_machine(self):
        # generate the inputs for the algorithm
        inputs = list()
        inputs.append({"type": "MemoryMachine",
                       "value": self._machine})
        inputs.append({
            "type": "FileMachineFilePath",
            "value": os.path.join(self._report_default_directory,
                                  "fileMachine")})

        # ask for the file machine output
        outputs = list()
        outputs.append("FileMachine")

        # run executor
        pacman_executor = PACMANAlgorithmExecutor(
            algorithms=[], inputs=inputs,
            xml_paths=[], required_outputs=outputs,
            optional_algorithms=list(),
            do_timings=config.getboolean("Reports", "writeAlgorithmTimings"))
        pacman_executor.execute_mapping()

    def _run_algorithms_for_machine_gain(self, extra_outputs=None):
        # get inputs
        inputs = dict()
        algorithms = list()

        SpinnakerMainInterface.\
            _generate_inputs_and_algorithms_for_getting_machine(
                self, algorithms, inputs)

        # get outputs
        required_outputs = list()
        required_outputs.append("MemoryMachine")
        if extra_outputs is not None:
            required_outputs += list(extra_outputs)

        # get xmls
        xml_paths = list()
        xml_paths.append(os.path.join(
            os.path.dirname(interface_functions.__file__),
            "front_end_common_interface_functions.xml"))

        # run executor
        pacman_executor = PACMANAlgorithmExecutor(
            algorithms=algorithms, inputs=inputs,
            xml_paths=xml_paths, required_outputs=required_outputs,
            optional_algorithms=list(),
            do_timings=config.getboolean("Reports", "writeAlgorithmTimings"))
        pacman_executor.execute_mapping()

        # get machine object and transceiver
        self._machine = pacman_executor.get_item("MemoryMachine")
        if not config.getboolean("Machine", "virtual_board"):
            self._txrx = pacman_executor.get_item("MemoryTransceiver")

    def run(self, run_time):
        # set up the correct dsg algorithm
        if self._user_dsg_algorithm is None:
            if len(self._partitioned_graph.subvertices) != 0:
                self.dsg_algorithm = \
                    "FrontEndCommonPartitionedGraphDataSpecificationWriter"
            elif len(self._partitionable_graph.vertices) != 0:
                self.dsg_algorithm = \
                    "FrontEndCommonPartitionableGraphDataSpecificationWriter"
        else:
            self.dsg_algorithm = self._user_dsg_algorithm

        # run normal procedure
        SpinnakerMainInterface.run(self, run_time)

    @property
    def machine(self):
        """
        get machine object
        :return:
        """
        if self._machine is None:
            self._run_algorithms_for_machine_gain()
        return self._machine

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}"\
            .format(self._hostname)
