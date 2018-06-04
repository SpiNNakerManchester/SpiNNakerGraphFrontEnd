from enum import Enum

from data_specification.enums import DataType
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, SDRAMResource, \
    DTCMResource, CPUCyclesPerTickResource

from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants

from spinn_utilities.overrides import overrides


class SDPReceiverMachineVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):

    __slots__ = [
        # keys to transmit with i think
        '_keys'
    ]

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('N_KEYS', 1),
               ('KEYS', 2)])
    N_KEYS_REGION_SIZE = 4
    BYTES_PER_FIELD = 4

    def __init__(self, keys):
        MachineVertex.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        self._keys = keys

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        return self.get_static_resources(self._keys)

    @staticmethod
    def get_static_resources(keys):
        return ResourceContainer(
            sdram=SDRAMResource(
                constants.SYSTEM_BYTES_REQUIREMENT +
                SDPReceiverMachineVertex.N_KEYS_REGION_SIZE +
                SDPReceiverMachineVertex._calculate_sdram_for_keys(keys)),
            dtcm=DTCMResource(0),
            cpu_cycles=CPUCyclesPerTickResource(0))

    @staticmethod
    def _calculate_sdram_for_keys(keys):
        return SDPReceiverMachineVertex.BYTES_PER_FIELD * len(keys)

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "sdp_receiver.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info,
            iptags, reverse_iptags, machine_time_step, time_scale_factor):
        self._reserve_memory_regions(spec)
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))
        spec.switch_write_focus(self.DATA_REGIONS.N_KEYS.value)
        spec.write_value(len(self._n_keys), DataType.UINT32)
        spec.end_specification()

    def _reserve_memory_regions(self, spec):
        spec.reserve_memory_region(
            self.DATA_REGIONS.SYSTEM.value(),
            constants.SYSTEM_BYTES_REQUIREMENT, label="system region")
        spec.reserve_memory_region(
            self.DATA_REGIONS.N_KEYS.value(),
            self.N_KEYS_REGION_SIZE, label="n_keys region")
        spec.reserve_memory_region(
            self.DATA_REGIONS.KEYS.value(),
            self._calculate_sdram_for_keys(self.keys),
            label="keys region")
