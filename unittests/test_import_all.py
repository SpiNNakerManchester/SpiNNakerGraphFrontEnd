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
import unittest
import spinn_utilities.package_loader as package_loader

# These are scripts so can not be tested this way.
# They are covered in integration tests
EXCLUSIONS = ["spinnaker_graph_front_end.examples.Conways."
              "no_edges_examples.conways_no_edges",

              "spinnaker_graph_front_end.examples.Conways."
              "one_no_graph_example.conways_no_graph",

              "spinnaker_graph_front_end.examples.Conways."
              "partitioned_example_a_no_vis_no_buffer.conways_partitioned",

              "spinnaker_graph_front_end.examples.Conways."
              "partitioned_example_b_no_vis_buffer.conways_partitioned",

              "spinnaker_graph_front_end.examples.hello_world.hello_world",
              "spinnaker_graph_front_end.examples.template.python_template",

              "spinnaker_graph_front_end.examples.test_extra_monitor.main",

              "spinnaker_graph_front_end.examples.test_fixed_router."
              "hello_world",
              "spinnaker_graph_front_end.examples.test_fixed_router."
              "hello_world_vertex_clone",

              "spinnaker_graph_front_end.examples."
              "test_fixed_router_transmitter_reciever.hello_world",

              "spinnaker_graph_front_end.examples.test_timer_setup_cost."
              "test_timer_setup_cost"]


class ImportAllModule(unittest.TestCase):

    def test_import_all(self):
        if os.environ.get('CONTINUOUS_INTEGRATION', 'false').lower() == 'true':
            package_loader.load_module("spinnaker_graph_front_end",
                                       exclusions=EXCLUSIONS,
                                       remove_pyc_files=False)
        else:
            package_loader.load_module("spinnaker_graph_front_end",
                                       exclusions=EXCLUSIONS,
                                       remove_pyc_files=True)
