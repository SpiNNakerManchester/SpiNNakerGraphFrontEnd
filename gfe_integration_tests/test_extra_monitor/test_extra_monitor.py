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

import time
import os
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.utilities.helpful_functions import (
    get_region_base_address_offset, n_word_struct)
from spinn_front_end_common.utility_models import StreamingContextManager
import spinnaker_graph_front_end as sim
from gfe_integration_tests.test_extra_monitor.sdram_writer import (
    SDRAMWriter, DataRegions)
from spinnaker_testbase import BaseTestCase

_GATHERER_MAP = 'VertexToEthernetConnectedChipMapping'
_TRANSFER_SIZE_MEGABYTES = 20


def get_data_region_address(placement, region):
    # Get the App Data for the core
    transceiver = FecDataView.get_transceiver()
    app_data_base_address = transceiver.get_cpu_information_from_core(
        placement.x, placement.y, placement.p).user[0]

    # Get the provenance region base address
    address_location = get_region_base_address_offset(
        app_data_base_address, region.value)
    return transceiver.read_word(placement.x, placement.y, address_location)


def check_data(data):
    # check data is correct here
    ints = n_word_struct(len(data) // 4).unpack(data)
    start_value = 0
    for value in ints:
        if value != start_value:
            print("should be getting {}, but got {}".format(
                start_value, value))
            start_value = value + 1
        else:
            start_value += 1


def _do_transfer(gatherer, receiver_placement, writer_placement, writer_vertex):
    """
    :param .DataSpeedUpPacketGatherMachineVertex gatherer:
    :param .Placement receiver_placement:
    :param .Placement writer_placement:
    :param SDRAMWriter writer_vertex:
    :rtype: bytearray
    """
    with StreamingContextManager(FecDataView.iterate_gathers()):
        return gatherer.get_data(
            extra_monitor=receiver_placement.vertex,
            placement=receiver_placement,
            memory_address=get_data_region_address(
                writer_placement, DataRegions.DATA),
            length_in_bytes=writer_vertex.mbs_in_bytes)


def _get_gatherer_for_monitor(monitor):
    placement = FecDataView.get_placement_of_vertex(monitor)
    chip = FecDataView.get_chip_at(placement.x, placement.y)
    # pylint: disable=protected-access
    return FecDataView.get_gatherer_by_xy(
        chip.nearest_ethernet_x, chip.nearest_ethernet_y)


class TestExtraMonitors(BaseTestCase):

    def check_extra_monitor(self):
        mbs = _TRANSFER_SIZE_MEGABYTES

        # setup system
        sim.setup(model_binary_folder=os.path.dirname(__file__),
                  n_chips_required=2)

        # build verts
        writer_vertex = SDRAMWriter(mbs)

        # add verts to graph
        sim.add_machine_vertex_instance(writer_vertex)
        sim.run(12)

        writer_placement = FecDataView.get_placement_of_vertex(
            writer_vertex)

        # pylint: disable=protected-access

        receiver_monitor = FecDataView.get_monitor_by_xy(
            writer_placement.x, writer_placement.y)
        receiver_plt = FecDataView.get_placement_of_vertex(receiver_monitor)
        gatherer = _get_gatherer_for_monitor(writer_vertex)

        start = float(time.time())

        data = _do_transfer(
            gatherer, receiver_plt, writer_placement, writer_vertex)

        end = float(time.time())

        print(f"time taken to extract {mbs} MB is {end - start}. "
              f"Transfer rate: {(mbs * 8) / (end - start)} Mb/s")

        check_data(data)

        sim.stop()

    def test_extra_monitors(self):
        self.runsafe(self.check_extra_monitor)
