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
import logging
from types import ModuleType
from typing import List, Optional, Tuple
import sys

from spinn_utilities.abstract_base import abstractmethod
from spinn_utilities.overrides import overrides
from spinn_utilities.log import FormatAdapter

from spinnman.model.enums import ExecutableType

from pacman.model.graphs.common import Slice
from pacman.model.graphs.machine import MachineVertex
from pacman.model.placements import Placement
from pacman.model.resources import AbstractSDRAM

from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.data import FecDataView
from spinn_front_end_common.interface.buffer_management import (
    recording_utilities)
from spinn_front_end_common.interface.ds import DataSpecificationGenerator

from spinn_front_end_common.utilities.data_utils import (
    generate_system_data_region)
log = FormatAdapter(logging.getLogger(__file__))


class SimulatorVertex(MachineVertex, AbstractHasAssociatedBinary):
    """
    A machine vertex that is implemented by a binary APLX that supports
    the `spin1_api` simulation control protocol.
    """

    __slots__ = ["_binary_name", "__front_end"]

    def __init__(self, label: Optional[str], binary_name: str,
                 vertex_slice: Optional[Slice] = None):
        """
        :param label:
            The label for the vertex.
        :param binary_name:
            The name of the APLX implementing the vertex.
        :param vertex_slice:
            The slice of the application vertex that this machine vertex
            implements.
        """
        super().__init__(label, vertex_slice=vertex_slice)
        self._binary_name = binary_name
        if not binary_name.lower().endswith(".aplx"):
            log.warning("APLX protocol used but name not matching; "
                        "is {} misnamed?", binary_name)
        # Magic import
        self.__front_end = sys.modules["spinnaker_graph_front_end"]

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self) -> str:
        return self._binary_name

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self) -> ExecutableType:
        return ExecutableType.USES_SIMULATION_INTERFACE

    @property
    @abstractmethod
    @overrides(MachineVertex.sdram_required)
    def sdram_required(self) -> AbstractSDRAM:
        raise NotImplementedError

    @property
    def front_end(self) -> ModuleType:
        """
        The main front end that is handling this simulator vertex.
        """
        return self.__front_end

    @property
    def placement(self) -> Placement:
        """
        Get the placement of this vertex.

        .. note::
            Only valid *after* the simulation has run!
        """
        return FecDataView.get_placement_of_vertex(self)

    def get_recording_channel_data(
            self, recording_id: int) -> Tuple[bytes, bool]:
        """
        Get the data from a recording channel. The simulation must have
        :py:func:`spinnaker_graph_front_end.run` before this will work,
        and the vertex must set up the recording region beforehand.

        :param recording_id:
            Which recording channel to fetch
        :return: the data, and whether any data was lost
        """
        buffer_manager = FecDataView.get_buffer_manager()
        return buffer_manager.get_recording(self.placement, recording_id)

    def generate_system_region(self, spec: DataSpecificationGenerator,
                               region_id: int = 0) -> None:
        """
        Generate the system region for the data specification. Assumes that
        the vertex uses the system timestep and time scale factor.

        .. note::
            Do not use this with untimed vertices.

        :param spec: The data specification being built
        :param region_id:
            Which region is the system region.
            Defaults to 0 because it is almost always the first one.
        """
        generate_system_data_region(spec, region_id, self)

    def generate_recording_region(
            self, spec: DataSpecificationGenerator, region_id: int,
            channel_sizes: List[int]) -> None:
        """
        Generate the recording region for the data specification.

        :param spec: The data specification being built
        :param region_id:
            Which region is the recording region.
        """
        spec.reserve_memory_region(
            region=region_id,
            size=recording_utilities.get_recording_header_size(
                len(channel_sizes)),
            label="Recording")
        spec.switch_write_focus(region_id)
        spec.write_array(recording_utilities.get_recording_header_array(
            channel_sizes))
