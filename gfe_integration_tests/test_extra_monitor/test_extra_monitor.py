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

import struct
import time
import os
import spinnaker_graph_front_end as sim
from spinn_front_end_common.utilities import globals_variables
from data_specification.utility_calls import get_region_base_address_offset
from gfe_integration_tests.test_extra_monitor.sdram_writer import SDRAMWriter

_ONE_WORD = struct.Struct("<I")
_MONITOR_VERTICES = 'MemoryExtraMonitorVertices'
_GATHERER_MAP = 'MemoryMCGatherVertexToEthernetConnectedChipMapping'
_TRANSFER_SIZE_MEGABYTES = 20


def get_data_region_address(transceiver, placement, region):
    # Get the App Data for the core
    app_data_base_address = transceiver.get_cpu_information_from_core(
        placement.x, placement.y, placement.p).user[0]

    # Get the provenance region base address
    base_address_offset = get_region_base_address_offset(
        app_data_base_address, region.value)
    return _ONE_WORD.unpack(transceiver.read_memory(
        placement.x, placement.y, base_address_offset, _ONE_WORD.size))[0]


def check_data(data):
    # check data is correct here
    ints = struct.unpack("<{}I".format(len(data) // 4), data)
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


def test_extra_monitor():
    mbs = _TRANSFER_SIZE_MEGABYTES

    # setup system
    globals_variables.unset_simulator()
    sim.setup(model_binary_folder=os.path.dirname(__file__),
              n_chips_required=2)

    # build verts
    writer_vertex = SDRAMWriter(mbs)

    # add verts to graph
    sim.add_machine_vertex_instance(writer_vertex)
    sim.run(12)

    writer_placement = sim.placements().get_placement_of_vertex(writer_vertex)
    writer_chip = sim.machine().get_chip_at(
        writer_placement.x, writer_placement.y)

    # pylint: disable=protected-access
    outputs = sim.globals_variables.get_simulator()._last_run_outputs
    monitor_vertices = outputs[_MONITOR_VERTICES]
    gatherers = outputs[_GATHERER_MAP]

    receiver_plt = _get_monitor_placement(monitor_vertices, writer_placement)
    gatherer = gatherers[
        writer_chip.nearest_ethernet_x, writer_chip.nearest_ethernet_y]

    start = float(time.time())

    with gatherer.streaming(
            gatherers.values(), sim.transceiver(), monitor_vertices,
            sim.placements()):
        data = gatherer.get_data(
            receiver_plt, get_data_region_address(
                sim.transceiver(), writer_placement,
                SDRAMWriter.DATA_REGIONS.DATA),
            writer_vertex.mbs_in_bytes, fixed_routes=None)

    end = float(time.time())

    print("time taken to extract {} MB is {}. Transfer rate: {} Mb/s".format(
        mbs, end - start, (mbs * 8) / (end - start)))

    check_data(data)

    sim.stop()
