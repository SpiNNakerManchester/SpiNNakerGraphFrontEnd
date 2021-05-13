# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from spinn_utilities.config_holder import (
    get_config_int, get_config_str, set_config)
from spinn_utilities.abstract_base import AbstractBase
from spinn_utilities.log import FormatAdapter
from spinn_front_end_common.interface.abstract_spinnaker_base import (
    AbstractSpinnakerBase)
from spinn_front_end_common.utilities import SimulatorInterface
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.utilities.failed_state import FailedState
from spinnaker_graph_front_end.config_setup import reset_configs
from ._version import __version__ as version

logger = FormatAdapter(logging.getLogger(__name__))


def _is_allocated_machine():
    return (get_config_str("Machine", "spalloc_server") or
            get_config_str("Machine", "remote_spinnaker_url"))


class GraphFrontEndSimulatorInterface(
        SimulatorInterface, metaclass=AbstractBase):
    """ The simulator interface exported by the graph front end. A very thin\
        layer over the capabilities of the Front End Common package.
    """
    __slots__ = ()


class SpiNNaker(AbstractSpinnakerBase, GraphFrontEndSimulatorInterface):
    """ The implementation of the SpiNNaker simulation interface.

    .. note::
        You should not normally instantiate this directly from user code.
        Call :py:func:`~spinnaker_graph_front_end.setup` instead.
    """
    #: The base name of the configuration file (but no path)
    __slots__ = (
        "_user_dsg_algorithm"
    )

    def __init__(
            self, executable_finder, host_name=None, graph_label=None,
            database_socket_addresses=(), dsg_algorithm=None,
            n_chips_required=None, n_boards_required=None,
            extra_pre_run_algorithms=(),
            extra_post_run_algorithms=(), time_scale_factor=None,
            machine_time_step=None, extra_xml_paths=()):
        """
        :param executable_finder:
            How to find the executables
        :type executable_finder:
            ~spinn_front_end_common.utilities.utility_objs.ExecutableFinder
        :param str host_name:
            The SpiNNaker machine address
        :param str graph_label:
            A label for the graph
        :param database_socket_addresses:
            Extra sockets that will want to be notified about the location of
            the runtime database.
        :type database_socket_addresses:
            ~collections.abc.Iterable(~spinn_utilities.socket_address.SocketAddress)
        :param str dsg_algorithm:
            Algorithm to use for generating data
        :param int n_chips_required:
            How many chips are required.
            *Prefer ``n_boards_required`` if possible.*
        :param int n_boards_required:
            How many boards are required. Unnecessary with a local board.
        :param ~collections.abc.Iterable(str) extra_pre_run_algorithms:
            The names of any extra algorithms to call before running
        :param ~collections.abc.Iterable(str) extra_post_run_algorithms:
            The names of any extra algorithms to call after running
        :param int time_scale_factor:
            The time slow-down factor
        :param int machine_time_step:
            The size of the machine time step, in microseconds
        :param ~collections.abc.Iterable(str) extra_xml_paths:
            Where to look for algorithm descriptors
        """
        # DSG algorithm store for user defined algorithms
        self._user_dsg_algorithm = dsg_algorithm

        front_end_versions = [("SpiNNakerGraphFrontEnd", version)]

        super().__init__(
            executable_finder=executable_finder,
            graph_label=graph_label,
            database_socket_addresses=database_socket_addresses,
            extra_algorithm_xml_paths=extra_xml_paths,
            n_chips_required=n_chips_required,
            n_boards_required=n_boards_required,
            front_end_versions=front_end_versions)

        if _is_allocated_machine() and \
                n_chips_required is None and n_boards_required is None:
            self.set_n_boards_required(1)

        extra_mapping_inputs = dict()
        self.update_extra_mapping_inputs(extra_mapping_inputs)
        self.prepend_extra_pre_run_algorithms(extra_pre_run_algorithms)
        self.extend_extra_post_run_algorithms(extra_post_run_algorithms)

        self.set_up_machine_specifics(host_name)
        self.set_up_timings(machine_time_step, time_scale_factor)

        # if not set at all, set to 1 for real time execution.
        if get_config_int("Machine", "time_scale_factor") is None:
            set_config("Machine", "time_scale_factor", 1)
        logger.info(f'Setting time scale factor to '
                    f'{get_config_int("Machine", "time_scale_factor")}.')
        logger.info(f'Setting machine time step to '
                    f'{get_config_int("Machine", "machine_time_step")} '
                    f'micro-seconds.')

    @property
    def is_allocated_machine(self):
        """ Is this an allocated machine? Otherwise, it is local.

        :rtype: bool
        """
        return _is_allocated_machine()

    def run(self, run_time):
        """ Run a simulation for a fixed amount of time

        :param int run_time: the run duration in milliseconds.
        """
        # pylint: disable=arguments-differ

        # set up the correct DSG algorithm
        if self._user_dsg_algorithm is not None:
            self.dsg_algorithm = self._user_dsg_algorithm

        # run normal procedure
        super().run(run_time)

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}".format(
            self._hostname)


class _GraphFrontEndFailedState(GraphFrontEndSimulatorInterface, FailedState):
    """ The special object that indicates that the simulator has failed.
    """
    __slots__ = ()


# At import time change the default FailedState
globals_variables.set_failed_state(_GraphFrontEndFailedState())
reset_configs()
