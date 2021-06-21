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
_CI = os.environ.get('CONTINUOUS_INTEGRATION', 'false').lower()


class ImportAllModule(unittest.TestCase):

    # no unittest_setup to check all imports work without it

    def test_import_all(self):
        package_loader.load_module("spinnaker_graph_front_end",
                                   remove_pyc_files=(_CI != 'true'))
