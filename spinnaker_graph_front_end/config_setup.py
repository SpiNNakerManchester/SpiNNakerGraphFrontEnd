# Copyright (c) 2017 The University of Manchester
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

"""
Utilities for setting up the global configuration.
"""

import os
from spinn_utilities.config_holder import (
    add_default_cfg, clear_cfg_files)
from spinn_front_end_common.interface.config_setup import add_spinnaker_cfg
from spinn_front_end_common.data.fec_data_writer import FecDataWriter

#: The name of the configuration file
GFE_CFG = "spiNNakerGraphFrontEnd.cfg"


def add_gfe_cfg() -> None:
    """
    Adds the Graph Front end cfg default file and all previous ones
    """
    add_spinnaker_cfg()  # This add its dependencies too
    add_default_cfg(os.path.join(os.path.dirname(__file__), GFE_CFG))


def unittest_setup() -> None:
    """
    Does all the steps that may be required before a unit test.

    Resets the configurations so only the local default configurations are
    included.
    The user configuration is *not* included!

    Actual loading of the cfg file is done by config_holder
    if and only if config values are needed.

    .. note::
         This method should only be called from spinnaker_graph_front_end tests
         that do not call :py:func:`~spinnaker_graph_front_end.setup`.
    """
    clear_cfg_files(True)
    add_gfe_cfg()
    FecDataWriter.mock()
