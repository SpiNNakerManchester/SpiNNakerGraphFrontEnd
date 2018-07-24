# common front end imports
from spinn_front_end_common.interface.abstract_spinnaker_base \
    import AbstractSpinnakerBase
from spinn_front_end_common.utilities import globals_variables

# graph front end imports
from spinnaker_graph_front_end.utilities.graph_front_end_failed_state \
    import GraphFrontEndFailedState
from spinnaker_graph_front_end.graph_front_end_simulator_interface \
    import GraphFrontEndSimulatorInterface
from ._version import __version__ as version

# general imports
import logging
import os

logger = logging.getLogger(__name__)

SPALLOC_CORES = 48

# At import time change the default FailedState
globals_variables.set_failed_state(GraphFrontEndFailedState())


def _is_allocated_machine(config):
    return (config.get("Machine", "spalloc_server") != "None" or
            config.get("Machine", "remote_spinnaker_url") != "None")


class SpiNNaker(AbstractSpinnakerBase, GraphFrontEndSimulatorInterface):

    CONFIG_FILE_NAME = "spiNNakerGraphFrontEnd.cfg"
    VALIDATION_CONFIG_NAME = "validation_config.cfg"

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=None, dsg_algorithm=None,
            n_chips_required=None, extra_pre_run_algorithms=None,
            extra_post_run_algorithms=None, time_scale_factor=None,
            machine_time_step=None, default_config_paths=None,
            extra_xml_paths=None):

        global CONFIG_FILE_NAME, SPALLOC_CORES

        # dsg algorithm store for user defined algorithms
        self._user_dsg_algorithm = dsg_algorithm

        # create xml path for where to locate GFE related functions when
        # using auto pause and resume
        if extra_xml_paths is None:
            extra_xml_paths = list()

        front_end_versions = [("SpiNNakerGraphFrontEnd", version)]

        # support extra configs
        this_default_config_paths = list()
        this_default_config_paths.append(
            os.path.join(os.path.dirname(__file__), self.CONFIG_FILE_NAME))
        if default_config_paths is not None:
            this_default_config_paths.extend(default_config_paths)

        super(SpiNNaker, self).__init__(
            configfile=self.CONFIG_FILE_NAME,
            executable_finder=executable_finder,
            graph_label=graph_label,
            database_socket_addresses=database_socket_addresses,
            extra_algorithm_xml_paths=extra_xml_paths,
            n_chips_required=n_chips_required,
            default_config_paths=this_default_config_paths,
            validation_cfg=os.path.join(os.path.dirname(__file__),
                                        self.VALIDATION_CONFIG_NAME),
            front_end_versions=front_end_versions)

        extra_mapping_inputs = dict()
        extra_mapping_inputs["CreateAtomToEventIdMapping"] = self.config.\
            getboolean("Database", "create_routing_info_to_atom_id_mapping")

        self.update_extra_mapping_inputs(extra_mapping_inputs)
        self.prepend_extra_pre_run_algorithms(extra_pre_run_algorithms)
        self.extend_extra_post_run_algorithms(extra_post_run_algorithms)

        self.set_up_machine_specifics(host_name)
        self.set_up_timings(machine_time_step, time_scale_factor)

        # if not set at all, set to 1 for real time execution.
        if self._time_scale_factor is None:
            self._time_scale_factor = 1

        logger.info("Setting time scale factor to {}."
                    .format(self._time_scale_factor))
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
        if self._user_dsg_algorithm is not None:
            self.dsg_algorithm = self._user_dsg_algorithm

        # run normal procedure
        AbstractSpinnakerBase.run(self, run_time)

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}"\
            .format(self._hostname)
