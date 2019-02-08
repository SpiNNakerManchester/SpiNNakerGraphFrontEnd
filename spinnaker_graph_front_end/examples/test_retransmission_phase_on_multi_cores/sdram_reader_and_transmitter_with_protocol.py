from enum import Enum
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ConstantSDRAM, ResourceContainer
from spinn_front_end_common.abstract_models import (
    AbstractHasAssociatedBinary, AbstractProvidesNKeysForPartition)
from spinn_front_end_common.abstract_models.impl import (
    MachineDataSpecableVertex)
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.interface.simulation import simulation_utilities


class SDRAMReaderAndTransmitterWithProtocol(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        AbstractProvidesNKeysForPartition):

    SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024*1024
    KEY_REGION_SIZE = 8

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('CONFIG', 1)])

    def __init__(self, mbs):
        self._mbs = mbs * self.SDRAM_READING_SIZE_IN_BYTES_CONVERTER
        super(SDRAMReaderAndTransmitterWithProtocol, self).__init__(
            label="speed", constraints=None)

    @property
    def resources_required(self):
        return ResourceContainer(sdram=ConstantSDRAM(
            self._mbs + constants.SYSTEM_BYTES_REQUIREMENT +
            self.KEY_REGION_SIZE))

    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.SYSTEM_BYTES_REQUIREMENT

        # Reserve SDRAM space for memory areas:

        # Create the data regions for hello world
        self._reserve_memory_regions(spec, setup_size)

        # write data for the simulation data item
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # write key
        local_routing_info = \
            routing_info.get_routing_info_from_pre_vertex(self, "TRANSMIT")

        spec.switch_write_focus(self.DATA_REGIONS.CONFIG.value)
        first_key = local_routing_info.first_key
        spec.write_value(first_key)
        spec.write_value(self._mbs)

        # End-of-Spec:
        spec.end_specification()

    def _reserve_memory_regions(self, spec, system_size):
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.SYSTEM.value, size=system_size,
            label='systemInfo')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.CONFIG.value,
            size=self.KEY_REGION_SIZE,
            label="config")

    def get_binary_file_name(self):
        return "sdram_reader_and_transmitter_with_protocol.aplx"

    def get_n_keys_for_partition(self, partition, graph_mapper):
        return 3
