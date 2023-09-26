# Copyright (c) 2023 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ctypes import LittleEndianStructure, c_uint32, sizeof
from enum import IntEnum
import logging
import numpy
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM
from pacman.model.graphs.common.chip_and_core import ChipAndCore
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.data.fec_data_view import FecDataView
from spinnaker_graph_front_end.utilities import SimulatorVertex

logger = FormatAdapter(logging.getLogger(__name__))


class DataRegions(IntEnum):
    SYSTEM = 0
    CONFIG = 1


#: The name of the partition for sending data
PARTITION_NAME = "MC"


#: Config data structure
# typedef struct {
class ConfigData(LittleEndianStructure):
    _fields_ = [
        #: Key to send to neighbours with
        # uint32_t send_key;
        ("key", c_uint32),

        #: Mask to send to neighbours with
        # uint32_t send_mask;
        ("mask", c_uint32),

        #: How many times to send per time step
        # uint32_t sends_per_timestep;
        ("sends_per_timestep", c_uint32),

        #: Time between sends (calculated on host)
        # uint32_t time_between_sends_us;
        ("time_between_sends_us", c_uint32),

        #: Whether to write the route
        # uint32_t write_route;
        ("write_route", c_uint32)
    ]
# } config_data_t;


class LinkTestSendVertex(SimulatorVertex, MachineDataSpecableVertex):

    def __init__(self, x, y, sends_per_ts, write_route,
                 label=None):
        super().__init__(label, "link_test_sender.aplx")

        self.__x = x
        self.__y = y
        self.__sends_per_ts = sends_per_ts
        self.__write_route = write_route

    @overrides(SimulatorVertex.get_fixed_location)
    def get_fixed_location(self):
        return ChipAndCore(self.__x, self.__y)

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        return ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT +
            sizeof(ConfigData))

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        self.generate_system_region(spec, DataRegions.SYSTEM)

        # Make a config
        r_info = FecDataView.get_routing_infos()
        ts = FecDataView.get_simulation_time_step_us()
        config = (ConfigData * 1)()
        info = r_info.get_routing_info_from_pre_vertex(self, PARTITION_NAME)
        config[0].key = info.key
        config[0].mask = info.mask
        config[0].sends_per_timestep = self.__sends_per_ts
        config[0].time_between_sends_us = int((ts / 2) / self.__sends_per_ts)
        config[0].write_route = self.__write_route

        # Write config data
        spec.reserve_memory_region(
            DataRegions.CONFIG, sizeof(ConfigData), "Config")
        spec.switch_write_focus(DataRegions.CONFIG)
        spec.write_array(numpy.array(config).view("uint32"))

        # End-of-Spec:
        spec.end_specification()

    def get_n_keys_for_partition(self, partition_id):
        return self.__sends_per_ts
