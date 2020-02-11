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

from testfixtures import LogCapture
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
        with LogCapture() as lc:
            import spinnaker_graph_front_end.examples.hello_world.hello_world   # NOQA
            outputs = lc.records[-16:]
            for n in range(16):
                print(outputs[n].getMessage())
                assert(outputs[n].getMessage()[-13:-2] == "Hello world")
