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


def _get_monitor_placement(monitor_vertices, placement):
    """ Get the receiver placement on the same chip as a given placement
    """
    for vertex in monitor_vertices.values():
        vtx_plt = FecDataView.get_placement_of_vertex(vertex)
        if vtx_plt.x == placement.x and vtx_plt.y == placement.y:
            return vtx_plt
    raise Exception("no extra monitor on same chip as {}".format(placement))


def _do_transfer(gatherer, gatherers, monitor_vertices, receiver_placement,
                 writer_placement, writer_vertex):
    """
    :param .DataSpeedUpPacketGatherMachineVertex gatherer:
    :param dict(tuple(int,int),.DataSpeedUpPacketGatherMachineVertex) \
            gatherers:
    :param list(.ExtraMonitorSupportMachineVertex) monitor_vertices:
    :param .Placement receiver_placement:
    :param .Placement writer_placement:
    :param SDRAMWriter writer_vertex:
    :rtype: bytearray
    """
    with StreamingContextManager(
            gatherers.values(), FecDataView.get_transceiver(),
            monitor_vertices, FecDataView.get_placements()):
        return gatherer.get_data(
            extra_monitor=receiver_placement.vertex,
            placement=receiver_placement,
            memory_address=get_data_region_address(
                writer_placement, DataRegions.DATA),
            length_in_bytes=writer_vertex.mbs_in_bytes)


def _get_gatherer_for_monitor(monitor):
    placement = FecDataView.get_placement_of_vertex(monitor)
    chip = FecDataView.get_chip_at(placement.x, placement.y)
    the_sim = sim.globals_variables.get_simulator()
    # pylint: disable=protected-access
    gatherers = the_sim._vertex_to_ethernet_connected_chip_mapping
    return (
        gatherers, gatherers[chip.nearest_ethernet_x, chip.nearest_ethernet_y])


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
        monitor_vertices = sim.globals_variables.get_simulator().\
            _extra_monitor_to_chip_mapping

        receiver_plt = _get_monitor_placement(
            monitor_vertices, writer_placement)
        gatherers, gatherer = _get_gatherer_for_monitor(writer_vertex)

        start = float(time.time())

        data = _do_transfer(gatherer, gatherers, monitor_vertices, receiver_plt,
                            writer_placement, writer_vertex)

        end = float(time.time())

        print(f"time taken to extract {mbs} MB is {end - start}. "
              f"Transfer rate: {(mbs * 8) / (end - start)} Mb/s")

        check_data(data)

        sim.stop()

    def test_extra_monitors(self):
        self.runsafe(self.check_extra_monitor)
