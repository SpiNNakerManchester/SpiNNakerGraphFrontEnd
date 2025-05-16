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
import pytest

from spinnman.exceptions import SpinnmanException
from spinnman.model.enums import ExecutableType
from spinnaker_testbase import BaseTestCase

import spinnaker_graph_front_end as s
from gfe_integration_tests.test_rte.run_vertex import RunVertex


class TestRteStart(BaseTestCase):

    def check_rte_at_start(self) -> None:
        s.setup(model_binary_folder=os.path.dirname(__file__))
        s.add_machine_vertex_instance(
            RunVertex(
                "test_rte_start.aplx",
                ExecutableType.USES_SIMULATION_INTERFACE))
        with pytest.raises(SpinnmanException):
            s.run(1000)

    def test_rte_at_start(self) -> None:
        self.runsafe(self.check_rte_at_start)
