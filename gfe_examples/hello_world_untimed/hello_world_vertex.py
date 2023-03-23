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

from enum import IntEnum
import logging
from spinn_utilities.log import FormatAdapter
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import VariableSDRAM
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.utilities.constants import (
    SYSTEM_BYTES_REQUIREMENT, BYTES_PER_WORD)
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement)
from spinn_front_end_common.abstract_models import (
    AbstractGeneratesDataSpecification)
from spinn_front_end_common.interface.buffer_management.buffer_models import (
    AbstractReceiveBuffersToHost)
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinnaker_graph_front_end.utilities import SimulatorVertex
from spinnaker_graph_front_end.utilities.data_utils import (
    generate_steps_system_data_region)
import numpy

logger = FormatAdapter(logging.getLogger(__name__))


class DataRegions(IntEnum):
    """
    The data regions that the C code uses.
    """
    SYSTEM = 0
    PARAMS = 1
    STRING_DATA = 2


class Channels(IntEnum):
    """
    The recording channel IDs that the C code uses.
    """
    HELLO = 0


class HelloWorldVertex(
        SimulatorVertex, AbstractGeneratesDataSpecification,
        AbstractReceiveBuffersToHost):
    PARAMS_BASE_SIZE = BYTES_PER_WORD * 2

    _ENCODING = "ascii"

    def __init__(self, label):
        """
        :param int n_repeats: The number of times to repeat the label in total
        :param str label: The label, which will be printed
        """
        super().__init__(label, "hello_world.aplx")

        # Make the text fit at a word boundary
        self._text = label
        text_extra = len(label) % BYTES_PER_WORD
        if text_extra != 0:
            for _ in range(BYTES_PER_WORD - text_extra):
                self._text += ' '

    @property
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self):
        fixed = (
            SYSTEM_BYTES_REQUIREMENT +
            recording_utilities.get_recording_header_size(len(Channels)) +
            self.PARAMS_BASE_SIZE + len(self._text))
        variable = len(self._text)
        return VariableSDRAM(fixed, variable)

    @overrides(AbstractGeneratesDataSpecification.generate_data_specification)
    def generate_data_specification(self, spec, placement):
        # pylint: disable=arguments-differ

        # Generate the system data region for simulation .c requirements
        # Note that the time step and time scale factor are unused here
        generate_steps_system_data_region(spec, DataRegions.SYSTEM, self)

        # Create the data regions for hello world
        spec.reserve_memory_region(
            region=DataRegions.PARAMS,
            size=self.PARAMS_BASE_SIZE + len(self._text))

        # write data for the recording
        self.generate_recording_region(
            spec, DataRegions.STRING_DATA,
            [FecDataView.get_max_run_time_steps() * len(self._text)])

        # write the data
        spec.switch_write_focus(DataRegions.PARAMS)
        spec.write_value(len(self._text))
        spec.write_array(numpy.array(
            bytearray(self._text, self._ENCODING)).view("uint32"))

        # End-of-Spec:
        spec.end_specification()

    def read(self):
        """
        Get the data written into SDRAM.

        :return: string output
        """
        raw_data, missing_data = self.get_recording_channel_data(
            Channels.HELLO)
        if missing_data:
            raise ValueError("missing data!")
        return str(raw_data, self._ENCODING)

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        return [Channels.HELLO]

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, placement):
        return locate_memory_region_for_placement(
            placement, DataRegions.STRING_DATA)
