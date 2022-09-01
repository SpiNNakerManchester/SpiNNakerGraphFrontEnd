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


def test_profile():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(ProfiledVertex())
    s.run(50)
    s.stop()


if __name__ == "__main__":
    test_profile()
