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
from spinn_utilities.config_holder import get_config_str
from spinn_utilities.log import FormatAdapter
from spinn_front_end_common.interface.abstract_spinnaker_base import (
    AbstractSpinnakerBase)
from spinnaker_graph_front_end.config_setup import setup_configs
from ._version import __version__ as version

logger = FormatAdapter(logging.getLogger(__name__))


def _is_allocated_machine():
    return (get_config_str("Machine", "spalloc_server") or
            get_config_str("Machine", "remote_spinnaker_url"))


class SpiNNaker(AbstractSpinnakerBase):
    """ The implementation of the SpiNNaker simulation interface.

    .. note::
        You should not normally instantiate this directly from user code.
        Call :py:func:`~spinnaker_graph_front_end.setup` instead.
    """

    def __init__(
            self, host_name=None, graph_label=None,
            database_socket_addresses=(),
            n_chips_required=None, n_boards_required=None,
            time_scale_factor=None, machine_time_step=None):
        """
        :param str host_name:
            The SpiNNaker machine address
        :param str graph_label:
            A label for the graph
        :param database_socket_addresses:
            Extra sockets that will want to be notified about the location of
            the runtime database.
        :type database_socket_addresses:
            ~collections.abc.Iterable(~spinn_utilities.socket_address.SocketAddress)
        :param int n_chips_required:
            How many chips are required.
            *Prefer ``n_boards_required`` if possible.*
        :param int n_boards_required:
            How many boards are required. Unnecessary with a local board.
        :param int time_scale_factor:
            The time slow-down factor
        :param int machine_time_step:
            The size of the machine time step, in microseconds
        """
        # DSG algorithm store for user defined algorithms

        # At import time change the default FailedState
        setup_configs()

        front_end_versions = [("SpiNNakerGraphFrontEnd", version)]

        super().__init__(
            graph_label=graph_label,
            database_socket_addresses=database_socket_addresses,
            n_chips_required=n_chips_required,
            n_boards_required=n_boards_required,
            front_end_versions=front_end_versions)

        if _is_allocated_machine() and \
                n_chips_required is None and n_boards_required is None:
            self.set_n_boards_required(1)

        self.set_up_machine_specifics(host_name)
        self._data_writer.set_up_timings(
            machine_time_step, time_scale_factor, 1)

    @property
    def is_allocated_machine(self):
        """ Is this an allocated machine? Otherwise, it is local.

        :rtype: bool
        """
        return _is_allocated_machine()

    def __repr__(self):
        return "SpiNNaker Graph Front End object for machine {}".format(
            self._hostname)
