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

import time
import os
from spinn_front_end_common.utilities.utility_calls import (
    get_region_base_address_offset)
from data_specification.utility_calls import get_region_base_address_offset
from spinn_front_end_common.utilities.helpful_functions import n_word_struct
import spinnaker_graph_front_end as sim
from gfe_integration_tests.test_extra_monitor.sdram_writer import (
    SDRAMWriter, DataRegions)
from spinnaker_testbase import BaseTestCase

_MONITOR_VERTICES = 'MemoryExtraMonitorVertices'
_GATHERER_MAP = 'MemoryMCGatherVertexToEthernetConnectedChipMapping'
_TRANSFER_SIZE_MEGABYTES = 20


def get_data_region_address(transceiver, placement, region):
    # Get the App Data for the core
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
    for vertex in monitor_vertices:
        vtx_plt = sim.placements().get_placement_of_vertex(vertex)
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
    with gatherer.streaming(
            gatherers.values(), sim.transceiver(), monitor_vertices,
            sim.placements()):
        return gatherer.get_data(
            extra_monitor=receiver_placement.vertex,
            extra_monitor_placement=receiver_placement,
            memory_address=get_data_region_address(
                sim.transceiver(), writer_placement, DataRegions.DATA),
            length_in_bytes=writer_vertex.mbs_in_bytes,
            fixed_routes=None)


def _get_gatherer_for_monitor(monitor):
    placement = sim.placements().get_placement_of_vertex(monitor)
    chip = sim.machine().get_chip_at(placement.x, placement.y)
    the_sim = sim.globals_variables.get_simulator()
    # pylint: disable=protected-access
    gatherers = the_sim._last_run_outputs[_GATHERER_MAP]
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

        writer_placement = sim.placements().get_placement_of_vertex(writer_vertex)

        # pylint: disable=protected-access
        outputs = sim.globals_variables.get_simulator()._last_run_outputs
        monitor_vertices = outputs[_MONITOR_VERTICES]

        receiver_plt = _get_monitor_placement(monitor_vertices, writer_placement)
        gatherers, gatherer = _get_gatherer_for_monitor(writer_vertex)

        start = float(time.time())

        data = _do_transfer(gatherer, gatherers, monitor_vertices, receiver_plt,
                            writer_placement, writer_vertex)

        end = float(time.time())

        print("time taken to extract {} MB is {}. Transfer rate: {} Mb/s".format(
            mbs, end - start, (mbs * 8) / (end - start)))

        check_data(data)

        sim.stop()

    def test_extra_monitors(self):
        self.runsafe(self.check_extra_monitor)
