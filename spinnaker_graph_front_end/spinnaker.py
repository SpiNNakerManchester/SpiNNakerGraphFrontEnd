# Copyright (c) 2016 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from spinn_utilities.config_holder import get_config_str
from spinn_utilities.log import FormatAdapter
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.interface.abstract_spinnaker_base import (
    AbstractSpinnakerBase)
from spinn_front_end_common.interface.provenance import GlobalProvenance
from spinnaker_graph_front_end.config_setup import setup_configs
from ._version import __version__ as version

logger = FormatAdapter(logging.getLogger(__name__))


def _is_allocated_machine():
    return (get_config_str("Machine", "spalloc_server") or
            get_config_str("Machine", "remote_spinnaker_url"))


class SpiNNaker(AbstractSpinnakerBase):
    """
    The implementation of the SpiNNaker simulation interface.

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
            *Prefer* `n_boards_required` *if possible.*
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

        with GlobalProvenance() as db:
            db.insert_version("SpiNNakerGraphFrontEnd", version)

        self._data_writer.set_n_required(n_boards_required, n_chips_required)

        self._data_writer.set_up_timings(
            machine_time_step, time_scale_factor, 1)

    def __repr__(self):
        if FecDataView.has_ipaddress():
            return (f"SpiNNaker Graph Front End object "
                    f"for machine {FecDataView.get_ipaddress()}")
        else:
            return "SpiNNaker Graph Front End object no machine set"
