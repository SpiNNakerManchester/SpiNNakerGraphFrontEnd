
# common front end imports
from spinn_front_end_common.interface.spinnaker_main_interface import \
    SpinnakerMainInterface

# graph front end imports
from spinnaker_graph_front_end.utilities.conf import config

# general imports
import logging


logger = logging.getLogger(__name__)


class SpiNNaker(SpinnakerMainInterface):

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=None, dsg_algorithm=None,
            n_chips_required=None, extra_pre_run_algorithms=None,
            extra_post_run_algorithms=None, time_scale_factor=None,
            machine_time_step=None, extra_load_algorithms=None):

        # dsg algorithm store for user defined algorithms
        self._user_dsg_algorithm = dsg_algorithm

        # create xml path for where to locate GFE related functions when
        # using auto pause and resume
        extra_xml_path = list()

        extra_mapping_inputs = dict()
        extra_mapping_inputs["CreateAtomToEventIdMapping"] = config.getboolean(
            "Database", "create_routing_info_to_atom_id_mapping")

        if config.getboolean("Reports", "ReportsEnabled"):
            if config.getboolean("Reports", "writeSynapticReport"):
                if extra_load_algorithms is None:
                    extra_load_algorithms = list()
                    extra_load_algorithms.append("SynapticMatrixReport")

        SpinnakerMainInterface.__init__(
            self, config, graph_label=graph_label,
            executable_finder=executable_finder,
            database_socket_addresses=database_socket_addresses,
            extra_algorithm_xml_paths=extra_xml_path,
            extra_mapping_inputs=extra_mapping_inputs,
            n_chips_required=n_chips_required,
            extra_pre_run_algorithms=extra_pre_run_algorithms,
            extra_post_run_algorithms=extra_post_run_algorithms,
            extra_load_algorithms=extra_load_algorithms)

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

    @staticmethod
    @property
    def is_allocated_machine():
        return (
            config.get("Machine", "spalloc_server") != "None" or
            config.get("Machine", "remote_spinnaker_url") != "None"
        )

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
        SpinnakerMainInterface.run(self, run_time)

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}"\
            .format(self._hostname)
