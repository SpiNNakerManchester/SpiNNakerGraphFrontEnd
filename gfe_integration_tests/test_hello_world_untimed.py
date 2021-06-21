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
from spinnaker_testbase import ScriptChecker


class TestHelloWorldUntimed(ScriptChecker):

   def test_hello_world_untimed(self):
        with LogCapture("hello_world") as lc:
            self.check_script(
                "gfe_examples/hello_world_untimed/hello_world.py")

        for n, output in enumerate(lc.records):
            msg = output.getMessage()
            print(msg)
            expect = "Hello World {}  ".format(n)
            if n < 10:
                expect += " "
            assert msg.endswith(expect * 20)
