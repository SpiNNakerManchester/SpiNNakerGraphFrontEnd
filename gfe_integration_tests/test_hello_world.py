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
from spinn_front_end_common.utilities import globals_variables


class TestHelloWorld(unittest.TestCase):

    def setUp(self):
        globals_variables.unset_simulator()

    def test_hello_world(self):
        import spinnaker_graph_front_end.examples.hello_world as hw_dir
        class_file = hw_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.hello_world.hello_world   # NOQA

        from spinnaker_graph_front_end.examples.hello_world.hello_world_vertex\
            import HelloWorldVertex
        placements = spinnaker_graph_front_end.examples.hello_world.\
            hello_world.placements
        buffer_manager = spinnaker_graph_front_end.examples.hello_world.\
            hello_world.buffer_manager
        outputs = []
        for placement in sorted(placements.placements,
                                key=lambda p: (p.x, p.y, p.p)):
            if isinstance(placement.vertex, HelloWorldVertex):
                hello_world = placement.vertex.read(placement, buffer_manager)
                outputs.append("{}, {}, {} > {}".format(
                    placement.x, placement.y, placement.p, hello_world))

        assert(len(outputs) == 16)
        assert(outputs[-1] == "1, 0, 2 > bytearray(b'Hello world')")
