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
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.interface.abstract_spinnaker_base import (
    AbstractSpinnakerBase)
from spinn_front_end_common.interface.provenance import ProvenanceWriter
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
            self, n_chips_required=None, n_boards_required=None,
            time_scale_factor=None, machine_time_step=None):
        """
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

        super().__init__()

        with ProvenanceWriter() as db:
            db.insert_version("SpiNNakerGraphFrontEnd", version)

        self._data_writer.set_n_required(n_boards_required, n_chips_required)

        self._data_writer.set_up_timings(
            machine_time_step, time_scale_factor, 1)

    def __repr__(self):
        if FecDataView.has_ipaddress():
            return f"SpiNNaker Graph Front End object " \
                   f"for machine {FecDataView.get_ipaddress()}"
        else:
            return "SpiNNaker Graph Front End object no machine set"
