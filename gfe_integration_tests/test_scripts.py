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
from unittest import SkipTest  # pylint: disable=unused-import


class TestScripts(ScriptChecker):
    """
    This file tests the scripts as configured in script_builder.py

    Please do not manually edit this file.
    It is rebuilt each time SpiNNakerManchester/IntegrationTests is run

    If it is out of date please edit and run script_builder.py
    Then the new file can be added to github for reference only.
    """
    # flake8: noqa

    def test_spinnaker_graph_front_end_examples_Conways_one_no_graph_example_conways_no_graph(self):
        self.check_script("examples/Conways/one_no_graph_example/conways_no_graph.py")

    def test_spinnaker_graph_front_end_examples_Conways_partitioned_example_a_no_vis_no_buffer_conways_basic_cell(self):
        self.check_script("examples/Conways/partitioned_example_a_no_vis_no_buffer/conways_basic_cell.py")

    def test_spinnaker_graph_front_end_examples_Conways_partitioned_example_a_no_vis_no_buffer_conways_partitioned(self):
        self.check_script("examples/Conways/partitioned_example_a_no_vis_no_buffer/conways_partitioned.py")

    def test_spinnaker_graph_front_end_examples_Conways_partitioned_example_b_no_vis_buffer_conways_basic_cell(self):
        self.check_script("examples/Conways/partitioned_example_b_no_vis_buffer/conways_basic_cell.py")

    def test_spinnaker_graph_front_end_examples_Conways_partitioned_example_b_no_vis_buffer_conways_partitioned(self):
        self.check_script("examples/Conways/partitioned_example_b_no_vis_buffer/conways_partitioned.py")

    def test_spinnaker_graph_front_end_examples_Conways_no_edges_examples_conways_basic_cell(self):
        self.check_script("examples/Conways/no_edges_examples/conways_basic_cell.py")

    def test_spinnaker_graph_front_end_examples_Conways_no_edges_examples_conways_no_edges(self):
        self.check_script("examples/Conways/no_edges_examples/conways_no_edges.py")
