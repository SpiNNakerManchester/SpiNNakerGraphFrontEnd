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
from pacman.model.graphs.application import ApplicationVertex


class SdramTestVertex(ApplicationVertex):
    """
    test vertex with fixed_sdram_value
    """

    def __init__(self, n_atoms):
        super().__init__()
        self.__n_atoms = n_atoms

    @property
    def n_atoms(self):
        return self.__n_atoms
