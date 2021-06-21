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
import pytest
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinnman.exceptions import SpinnmanException
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex


def test_rte_at_start():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(
        RunVertex(
            "test_rte_start.aplx",
            ExecutableType.USES_SIMULATION_INTERFACE))
    with pytest.raises(SpinnmanException):
        s.run(1000)
