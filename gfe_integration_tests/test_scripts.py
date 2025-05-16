# Copyright (c) 2019 The University of Manchester
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

from spinnaker_testbase import ScriptChecker


class TestScripts(ScriptChecker):
    """
    This file tests the scripts as configured in script_builder.py

    Please do not manually edit this file.
    It is rebuilt each time SpiNNakerManchester/IntegrationTests is run

    If it is out of date please edit and run script_builder.py
    Then the new file can be added to github for reference only.
    """
# flake8: noqa

    def test_gfe_examples_live_io_live_io(self) -> None:
        self.check_script("gfe_examples/live_io/live_io.py")

    def test_gfe_examples_live_io_live_io_vertex(self) -> None:
        self.check_script("gfe_examples/live_io/live_io_vertex.py")

    def test_gfe_examples_template_template_vertex(self) -> None:
        self.check_script("gfe_examples/template/template_vertex.py")

    def test_gfe_examples_template_python_template(self) -> None:
        self.check_script("gfe_examples/template/python_template.py")

    def test_gfe_examples_hello_world_untimed_hello_world(self) -> None:
        self.check_script("gfe_examples/hello_world_untimed/hello_world.py")

    def test_gfe_examples_hello_world_untimed_hello_world_vertex(self) -> None:
        self.check_script("gfe_examples/hello_world_untimed/hello_world_vertex.py")

    def test_gfe_examples_Conways_partitioned_example_b_no_vis_buffer_conways_partitioned(self) -> None:
        self.check_script("gfe_examples/Conways/partitioned_example_b_no_vis_buffer/conways_partitioned.py")

    def test_gfe_examples_Conways_partitioned_example_b_no_vis_buffer_conways_basic_cell(self) -> None:
        self.check_script("gfe_examples/Conways/partitioned_example_b_no_vis_buffer/conways_basic_cell.py")

    def test_gfe_examples_Conways_partitioned_example_a_no_vis_no_buffer_conways_partitioned(self) -> None:
        self.check_script("gfe_examples/Conways/partitioned_example_a_no_vis_no_buffer/conways_partitioned.py")

    def test_gfe_examples_Conways_partitioned_example_a_no_vis_no_buffer_conways_basic_cell(self) -> None:
        self.check_script("gfe_examples/Conways/partitioned_example_a_no_vis_no_buffer/conways_basic_cell.py")

    def test_gfe_examples_Conways_one_no_graph_example_conways_no_graph(self) -> None:
        self.check_script("gfe_examples/Conways/one_no_graph_example/conways_no_graph.py")

    def test_gfe_examples_Conways_no_edges_examples_conways_no_edges(self) -> None:
        self.check_script("gfe_examples/Conways/no_edges_examples/conways_no_edges.py")

    def test_gfe_examples_Conways_no_edges_examples_conways_basic_cell(self) -> None:
        self.check_script("gfe_examples/Conways/no_edges_examples/conways_basic_cell.py")

    def test_gfe_examples_sync_test_sync_test_vertex(self) -> None:
        self.check_script("gfe_examples/sync_test/sync_test_vertex.py")

    def test_gfe_examples_sync_test_sync_test(self) -> None:
        self.check_script("gfe_examples/sync_test/sync_test.py")

    def test_gfe_examples_hello_world_hello_world(self) -> None:
        self.check_script("gfe_examples/hello_world/hello_world.py")

    def test_gfe_examples_hello_world_hello_world_vertex(self) -> None:
        self.check_script("gfe_examples/hello_world/hello_world_vertex.py")
