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

""" test vertex used in many unit tests
"""
from spinn_utilities.overrides import overrides
from pacman_test_objects import SimpleTestVertex, MockMachineVertex


class SdramTestVertex(SimpleTestVertex):
    """
    test vertex with fixed_sdram_value
    """

    def __init__(self, n_atoms, fixed_sdram_value=None):
        super().__init__(n_atoms=n_atoms)
        self._fixed_sdram_value = fixed_sdram_value

    @property
    def fixed_sdram_value(self):
        return self._fixed_sdram_value

    @overrides(SimpleTestVertex.create_machine_vertex)
    def create_machine_vertex(
            self, vertex_slice, resources_required, label=None,
            constraints=None):
        return MockMachineVertex(
            resources_required, label, constraints, self, vertex_slice,
            sdram_requirement=self._fixed_sdram_value)
