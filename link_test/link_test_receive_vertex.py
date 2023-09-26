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
    UNKNOWN_KEYS = 3


#: Number of links on the machine
N_LINKS = 6

#: The name of the partition for sending data
PARTITION_NAME = "MC"


#: Config data structure
# typedef struct {
class ConfigData(LittleEndianStructure):
    _fields_ = [

        #: Keys to expect from neighbours
        # uint32_t receive_keys[N_LINKS];
        ("receive_keys", c_uint32 * N_LINKS),

        #: Masks to expect from neighbours
        # uint32_t receive_masks[N_LINKS];
        ("receive_masks", c_uint32 * N_LINKS),

        #: The number of packets received considered OK (calculated on host)
        # uint32_t packet_count_ok;
        ("packet_count_ok", c_uint32),

        #: Whether to write the routes
        # uint32_t write_route;
        ("write_routes", c_uint32)
    ]
# } config_data_t;


class LinkTestReceiveVertex(
        SimulatorVertex, MachineDataSpecableVertex,
        ProvidesProvenanceDataFromMachineImpl):

    def __init__(self, x, y, sends_per_ts, drops_per_ts_allowed, run_time,
                 write_routes, label=None):
        super().__init__(label, "link_test_receiver.aplx")

        self.__x = x
        self.__y = y
        self.__sends_per_ts = sends_per_ts
        self.__drops_per_ts_allowed = drops_per_ts_allowed
        self.__run_time = run_time
        self.__write_routes = write_routes
        self.__neighbours = [None] * 6
        self.__sources = set()
        self.__repeat_sources = set()

        self.__failed = False

    def set_neighbour(self, link, neighbour):
        if neighbour in self.__sources:
            print(f"Warning: {self.__x}, {self.__y} won't receive over link"
                  f" {link} as already receiving from elsewhere")
            self.__repeat_sources.add(link)
        else:
            self.__sources.add(neighbour)
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
        config = (ConfigData * 1)()
        for i in range(N_LINKS):
            if self.__neighbours[i] is None:
                config[0].receive_keys[i] = 0xFFFFFFFF
                config[0].receive_masks[i] = 0
            else:
                if self.__write_routes:
                    config[0].receive_keys[i] = self.__neighbours[i].base_key
                    config[0].receive_masks[i] = self.__neighbours[i].mask
                else:
                    info = r_info.get_routing_info_from_pre_vertex(
                        self.__neighbours[i], PARTITION_NAME)
                    config[0].receive_keys[i] = info.key
                    config[0].receive_masks[i] = info.mask
        config[0].packet_count_ok = (
            (self.__sends_per_ts - self.__drops_per_ts_allowed) *
            self.__run_time)
        config[0].write_routes = self.__write_routes

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
        link_count_ok, link_fail_ok, links_from_scamp, unknown_keys = (
            provenance_data)

        machine = FecDataView.get_machine()
        chip = machine.get_chip_at(x, y)
        ip = machine.get_chip_at(
            chip.nearest_ethernet_x, chip.nearest_ethernet_y).ip_address
        (lx, ly) = machine.get_local_xy(chip)
        loc = f"{x}, {y} ({lx}, {ly} on {ip})"

        with ProvenanceWriter() as db:
            for i in range(N_LINKS):
                this_link_count_ok = bool(link_count_ok & (1 << i))
                this_link_fail_ok = bool(link_fail_ok & (1 << i))
                this_link_enabled = bool(links_from_scamp & (1 << i))
                this_link_used = i not in self.__repeat_sources
                db.insert_core(
                    x, y, p, f"Link {i} count ok", this_link_count_ok)
                db.insert_core(
                    x, y, p, f"Link {i} fail ok", this_link_fail_ok)
                db.insert_core(
                    x, y, p, f"Link {i} enabled", this_link_enabled)
                db.insert_core(
                    x, y, p, f"Link {i} used", this_link_used)
                if (this_link_used and this_link_enabled and
                        not this_link_count_ok):

                    db.insert_report(f"Link {i} on {loc} failed to receive"
                                     " enough packets")
                    self.__failed = True
                if (this_link_used and this_link_enabled and
                        not this_link_fail_ok):
                    db.insert_report(f"Link {i} on {loc} received"
                                     " unexpected data at least once")
                    self.__failed = True
            db.insert_core(
                x, y, p, "Unknown keys", unknown_keys)
            if unknown_keys:
                db.insert_report(
                    f"Chip {loc} received {unknown_keys} unknown keys")
                self.__failed = True

    @property
    @overrides(ProvidesProvenanceDataFromMachineImpl._n_additional_data_items)
    def _n_additional_data_items(self):
        return len(EXTRA_PROVENANCE_DATA_ENTRIES)

    def check_failure(self):
        assert not self.__failed
