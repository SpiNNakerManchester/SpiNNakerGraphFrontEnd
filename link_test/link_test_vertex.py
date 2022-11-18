# Copyright (c) 2017-2022 The University of Manchester
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
from spinn_front_end_common.interface.provenance import (
    ProvidesProvenanceDataFromMachineImpl, ProvenanceWriter)
from spinn_front_end_common.data.fec_data_view import FecDataView
from spinnaker_graph_front_end.utilities import SimulatorVertex

logger = FormatAdapter(logging.getLogger(__name__))


class DataRegions(IntEnum):
    SYSTEM = 0
    CONFIG = 1
    PROVENANCE = 2


class EXTRA_PROVENANCE_DATA_ENTRIES(IntEnum):
    LINK_COUNT_OK = 0
    LINK_FAILS_OK = 1
    LINKS_FROM_SCAMP = 2


#: Number of links on the machine
N_LINKS = 6

#: The name of the partition for sending data
PARTITION_NAME = "MC"


#: Config data structure
# typedef struct {
class ConfigData(LittleEndianStructure):
    _fields_ = [
        #: Key to send to neighbours with
        # uint32_t send_key;
        ("key", c_uint32),

        #: Keys to expect from neighbours
        # uint32_t receive_keys[N_LINKS];
        ("receive_keys", c_uint32 * N_LINKS),

        #: How many times to send per time step
        # uint32_t sends_per_timestep;
        ("sends_per_timestep", c_uint32),

        #: Time between sends (calculated on host)
        # uint32_t time_between_sends_us;
        ("time_between_sends_us", c_uint32),

        #: The number of packets received considered OK (calculated on host)
        # uint32_t packet_count_ok;
        ("packet_count_ok", c_uint32)
    ]
# } config_data_t;


class LinkTestVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        ProvidesProvenanceDataFromMachineImpl):

    def __init__(self, x, y, sends_per_ts, drops_per_ts_allowed, run_time,
                 label=None):
        super().__init__(label, "link_test.aplx")

        self.__x = x
        self.__y = y
        self.__sends_per_ts = sends_per_ts
        self.__drops_per_ts_allowed = drops_per_ts_allowed
        self.__run_time = run_time
        self.__neighbours = [None] * 6

        self.__failed = False

    def set_neighbour(self, link, neighbour):
        self.__neighbours[link] = neighbour

    @overrides(SimulatorVertex.get_fixed_location)
    def get_fixed_location(self):
        return ChipAndCore(self.__x, self.__y)

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        return ConstantSDRAM(
            SYSTEM_BYTES_REQUIREMENT +
            sizeof(ConfigData) +
            self.get_provenance_data_size(len(EXTRA_PROVENANCE_DATA_ENTRIES)))

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, iptags, reverse_iptags):
        self.generate_system_region(spec, DataRegions.SYSTEM)
        self.reserve_provenance_data_region(spec)

        # Make a config
        r_info = FecDataView.get_routing_infos()
        ts = FecDataView.get_simulation_time_step_us()
        config = (ConfigData * 1)()
        config[0].key = r_info.get_first_key_from_pre_vertex(
            self, PARTITION_NAME)
        for i in range(N_LINKS):
            if self.__neighbours[i] is None:
                config[0].receive_keys[i] = 0xFFFFFFFF
            else:
                config[0].receive_keys[i] = \
                    r_info.get_first_key_from_pre_vertex(
                        self.__neighbours[i], PARTITION_NAME)
        config[0].sends_per_timestep = self.__sends_per_ts
        config[0].time_between_sends_us = int((ts / 2) / self.__sends_per_ts)
        config[0].packet_count_ok = (
            (self.__sends_per_ts - self.__drops_per_ts_allowed) *
            self.__run_time)

        # Write config data
        spec.reserve_memory_region(
            DataRegions.CONFIG, sizeof(ConfigData), "Config")
        spec.switch_write_focus(DataRegions.CONFIG)
        spec.write_array(numpy.array(config).view("uint32"))

        # End-of-Spec:
        spec.end_specification()

    @property
    @overrides(ProvidesProvenanceDataFromMachineImpl._provenance_region_id)
    def _provenance_region_id(self):
        return DataRegions.PROVENANCE

    @overrides(ProvidesProvenanceDataFromMachineImpl.
               parse_extra_provenance_items)
    def parse_extra_provenance_items(self, label, x, y, p, provenance_data):
        link_count_ok, link_fail_ok, links_from_scamp = provenance_data

        with ProvenanceWriter() as db:
            for i in range(N_LINKS):
                this_link_count_ok = bool(link_count_ok & (1 << i))
                this_link_fail_ok = bool(link_fail_ok & (1 << i))
                this_link_enabled = bool(links_from_scamp & (1 << i))
                db.insert_core(
                    x, y, p, f"Link {i} count ok", this_link_count_ok)
                db.insert_core(
                    x, y, p, f"Link {i} fail ok", this_link_fail_ok)
                db.insert_core(
                    x, y, p, f"Link {i} enabled", this_link_enabled)
                if this_link_enabled and not this_link_count_ok:
                    db.insert_report(f"Link {i} on {x}, {y} failed to receive"
                                     " enough packets")
                    self.__failed = True
                if this_link_enabled and not this_link_fail_ok:
                    db.insert_report(f"Link {i} on {x}, {y} received"
                                     " unexpected data at least once")
                    self.__failed = True

    @property
    @overrides(ProvidesProvenanceDataFromMachineImpl._n_additional_data_items)
    def _n_additional_data_items(self):
        return len(EXTRA_PROVENANCE_DATA_ENTRIES)

    def check_failure(self):
        assert not self.__failed
