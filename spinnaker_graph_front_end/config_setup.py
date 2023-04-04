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

import os
from spinn_utilities.config_holder import (
    clear_cfg_files, set_cfg_files)
from spinn_front_end_common.interface.config_setup import (
    add_default_cfg, add_spinnaker_cfg)
from spinn_front_end_common.data.fec_data_writer import FecDataWriter

#: The name of the configuration file
CONFIG_FILE_NAME = "spiNNakerGraphFrontEnd.cfg"


def setup_configs():
    """
    Sets up the configs including the user's cfg file.

    Clears out any previous read configs but does not load the new configs
    so a warning is generated if a config is used before setup is called.
    """
    clear_cfg_files(False)
    add_spinnaker_cfg()  # This add its dependencies too
    set_cfg_files(
        configfile=CONFIG_FILE_NAME,
        default=os.path.join(os.path.dirname(__file__), CONFIG_FILE_NAME))
    FecDataWriter.mock()


def unittest_setup():
    """
    Does all the steps that may be required before a unittest.

    Resets the configs so only the local default configs are included.
    The user cfg is *not* included!

    Unsets any previous simulators and tempdirs

    .. note::
         This file should only be called from sPyNNaker tests
         that do not call sim.setup
    """
    clear_cfg_files(True)
    add_spinnaker_cfg()  # This add its dependencies too
    add_default_cfg(os.path.join(os.path.dirname(__file__), CONFIG_FILE_NAME))
