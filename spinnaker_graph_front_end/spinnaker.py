import spinn_utilities.conf_loader as conf_loader

# common front end imports
from spinn_front_end_common.interface import AbstractSpinnakerBase
from spinn_front_end_common.utilities import globals_variables

# graph front end imports
import spinnaker_graph_front_end
from spinnaker_graph_front_end.utilities.graph_front_end_failed_state \
    import GraphFrontEndFailedState
from spinnaker_graph_front_end.graph_front_end_simulator_interface \
    import GraphFrontEndSimulatorInterface

# general imports
import logging

logger = logging.getLogger(__name__)

# christian check if can be inside
CONFIG_FILE_NAME = "spiNNakerGraphFrontEnd.cfg"

SPALLOC_CORES = 48

# At import time change the default FailedState
globals_variables.set_failed_state(GraphFrontEndFailedState())


def _is_allocated_machine(config):
    return (config.get("Machine", "spalloc_server") != "None" or
            config.get("Machine", "remote_spinnaker_url") != "None")


class SpiNNaker(AbstractSpinnakerBase, GraphFrontEndSimulatorInterface):

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=None, dsg_algorithm=None,
            n_chips_required=None, extra_pre_run_algorithms=None,
            extra_post_run_algorithms=None, time_scale_factor=None,
            machine_time_step=None):

        global CONFIG_FILE_NAME, SPALLOC_CORES
        # Read config file
        config = conf_loader.load_config(spinnaker_graph_front_end,
                                         CONFIG_FILE_NAME)

        # dsg algorithm store for user defined algorithms
        self._user_dsg_algorithm = dsg_algorithm

        # create xml path for where to locate GFE related functions when
        # using auto pause and resume
        extra_xml_path = list()

        extra_mapping_inputs = dict()
        extra_mapping_inputs["CreateAtomToEventIdMapping"] = config.getboolean(
            "Database", "create_routing_info_to_atom_id_mapping")

        if n_chips_required is None and _is_allocated_machine(config):
            n_chips_required = SPALLOC_CORES

        AbstractSpinnakerBase.__init__(
            self, config,
            graph_label=graph_label,
            executable_finder=executable_finder,
            database_socket_addresses=database_socket_addresses,
            extra_algorithm_xml_paths=extra_xml_path,
            extra_mapping_inputs=extra_mapping_inputs,
            n_chips_required=n_chips_required,
            extra_pre_run_algorithms=extra_pre_run_algorithms,
            extra_post_run_algorithms=extra_post_run_algorithms)

        # set up machine targeted data
        if machine_time_step is None:
            self._machine_time_step = \
                config.getint("Machine", "machineTimeStep")
        else:
            self._machine_time_step = machine_time_step

        self.set_up_machine_specifics(host_name)

        if time_scale_factor is None:
            self._time_scale_factor = \
                config.get("Machine", "timeScaleFactor")
            if self._time_scale_factor == "None":
                self._time_scale_factor = 1
            else:
                self._time_scale_factor = int(self._time_scale_factor)
        else:
            self._time_scale_factor = time_scale_factor

        logger.info("Setting time scale factor to {}."
                    .format(self._time_scale_factor))

        # get the machine time step
        logger.info("Setting machine time step to {} micro-seconds."
                    .format(self._machine_time_step))

    def get_machine_dimensions(self):
        """ Get the machine dimensions
        """
        machine = self.machine

        return {'x': machine.max_chip_x, 'y': machine.max_chip_y}

    @property
    def is_allocated_machine(self):
        return _is_allocated_machine(self.config)

    def add_socket_address(self, socket_address):
        """ Add a socket address to the list to be checked by the\
            notification protocol

        :param socket_address: the socket address
        :type socket_address:
        :rtype: None
        """
        self._add_socket_address(socket_address)

    def run(self, run_time):

        # set up the correct dsg algorithm
        if self._user_dsg_algorithm is None:
            self.dsg_algorithm = "FrontEndCommonGraphDataSpecificationWriter"
        else:
            self.dsg_algorithm = self._user_dsg_algorithm

        # run normal procedure
        AbstractSpinnakerBase.run(self, run_time)

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}"\
            .format(self._hostname)
