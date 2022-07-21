# Copyright (c) 2019-2021 The University of Manchester
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

    def test_gfe_examples_sync_test_sync_test(self):
        self.check_script("gfe_examples/sync_test/sync_test.py")

    def test_gfe_examples_sync_test_sync_test_vertex(self):
        self.check_script("gfe_examples/sync_test/sync_test_vertex.py")

    def test_gfe_examples_Conways_one_no_graph_example_conways_no_graph(self):
        self.check_script("gfe_examples/Conways/one_no_graph_example/conways_no_graph.py")

    def test_gfe_examples_Conways_partitioned_example_a_no_vis_no_buffer_conways_basic_cell(self):
        self.check_script("gfe_examples/Conways/partitioned_example_a_no_vis_no_buffer/conways_basic_cell.py")

    def test_gfe_examples_Conways_partitioned_example_a_no_vis_no_buffer_conways_partitioned(self):
        self.check_script("gfe_examples/Conways/partitioned_example_a_no_vis_no_buffer/conways_partitioned.py")

    def test_gfe_examples_Conways_partitioned_example_b_no_vis_buffer_conways_basic_cell(self):
        self.check_script("gfe_examples/Conways/partitioned_example_b_no_vis_buffer/conways_basic_cell.py")

    def test_gfe_examples_Conways_partitioned_example_b_no_vis_buffer_conways_partitioned(self):
        self.check_script("gfe_examples/Conways/partitioned_example_b_no_vis_buffer/conways_partitioned.py")

    def test_gfe_examples_Conways_no_edges_examples_conways_basic_cell(self):
        self.check_script("gfe_examples/Conways/no_edges_examples/conways_basic_cell.py")

    def test_gfe_examples_Conways_no_edges_examples_conways_no_edges(self):
        self.check_script("gfe_examples/Conways/no_edges_examples/conways_no_edges.py")

    def test_gfe_examples_hello_world_hello_world(self):
        self.check_script("gfe_examples/hello_world/hello_world.py")

    def test_gfe_examples_hello_world_hello_world_vertex(self):
        self.check_script("gfe_examples/hello_world/hello_world_vertex.py")

    def test_gfe_examples_hello_world_untimed_hello_world(self):
        self.check_script("gfe_examples/hello_world_untimed/hello_world.py")

    def test_gfe_examples_hello_world_untimed_hello_world_vertex(self):
        self.check_script("gfe_examples/hello_world_untimed/hello_world_vertex.py")

    def test_gfe_examples_template_python_template(self):
        self.check_script("gfe_examples/template/python_template.py")

    def test_gfe_examples_template_template_vertex(self):
        self.check_script("gfe_examples/template/template_vertex.py")
