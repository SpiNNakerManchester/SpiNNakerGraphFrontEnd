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

from spinnaker_testbase import RootScriptBuilder


class ScriptBuilder(RootScriptBuilder):
    """
    This file will recreate the test_scripts.py file

    To skip the too_long scripts run this script with a parameter
    """

    def build_intro_labs_scripts(self):
        # create_test_scripts supports test that are too long or exceptions

        # It does not matter if this picks up classes with no main
        # For those it just acts like test_import_all does
        self.create_test_scripts(
            ["spinnaker_graph_front_end/examples/Conways"])


if __name__ == '__main__':
    builder = ScriptBuilder()
    builder.build_intro_labs_scripts()
