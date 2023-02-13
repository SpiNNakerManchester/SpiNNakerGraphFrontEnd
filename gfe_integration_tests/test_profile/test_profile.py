# Copyright (c) 2017-2023 The University of Manchester
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
