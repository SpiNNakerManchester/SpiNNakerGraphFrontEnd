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
from spinn_front_end_common.utilities import globals_variables
from spinnaker_testbase import ScriptChecker


class TestHelloWorld(ScriptChecker):

    def setUp(self):
        globals_variables.unset_simulator()

    def test_hello_world(self):
        with LogCapture() as lc:
            self.check_script(
                "spinnaker_graph_front_end/examples/hello_world"
                "/hello_world.py")
            outputs = lc.records[-16:]
            for n in range(16):
                msg = outputs[n].getMessage()
                print(msg)
                test_text = "Hello world; " * 20
                assert(msg[-(len(test_text) + 2):-2] == test_text)
