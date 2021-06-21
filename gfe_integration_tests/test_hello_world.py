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

    def test_hello_world(self):
        with LogCapture("hello_world") as lc:
            self.check_script(
                "gfe_examples/hello_world/hello_world.py")

        test_text = "Hello world; " * 20
        for record in lc.records:
            msg = record.getMessage()
            print(msg)
            assert test_text in msg
