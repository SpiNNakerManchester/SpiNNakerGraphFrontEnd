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

import os
import traceback
import pytest
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinnman.exceptions import SpinnmanException
import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex


def test_rte_during_run():
    s.setup(model_binary_folder=os.path.dirname(__file__))
    s.add_machine_vertex_instance(RunVertex(
        "test_rte_during_run.aplx",
        ExecutableType.USES_SIMULATION_INTERFACE))
    with pytest.raises(SpinnmanException):
        try:
            s.run(1000)
        except Exception:
            traceback.print_exc()
            raise
