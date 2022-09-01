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

import os
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_profile.profiled_vertex import ProfiledVertex
from spinn_front_end_common.data.fec_data_view import FecDataView


def test_profile():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    vertex = ProfiledVertex()
    s.add_machine_vertex_instance(vertex)
    s.run(50)

    place = FecDataView.get_placement_of_vertex(vertex)
    folder = FecDataView.get_app_provenance_dir_path()

    s.stop()

    profile_file = os.path.join(
        folder, f"{place.x}_{place.y}_{place.p}_profile.txt")
    assert os.path.exists(profile_file)

    with open(profile_file, "r") as f:
        # Headings and lines
        f.readline()
        f.readline()

        # Next 2 lines should have profile data
        for i in range(2):
            line = f.readline()
            parts = line.split()
            assert len(parts) == 5
            assert parts[0] == "SDRAMWrite" or parts[0] == "DTCMWrite"
            assert int(parts[1]) == 25
            assert float(parts[3]) == 1.0
            assert float(parts[2]) == float(parts[4])


if __name__ == "__main__":
    test_profile()
