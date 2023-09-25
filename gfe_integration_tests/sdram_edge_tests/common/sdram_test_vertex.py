# Copyright (c) 2017 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
