from enum import Enum
import numpy

from data_specification.enums import DataType
from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, SDRAMResource, \
    DTCMResource, CPUCyclesPerTickResource

from spinn_front_end_common.abstract_models import \
    AbstractHasAssociatedBinary, AbstractProvidesNKeysForPartition
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.utilities import constants

from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import helpful_functions
from spinnman.messages.sdp import SDPMessage, SDPHeader


class SDPReceiverMachineVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        AbstractProvidesNKeysForPartition):

    __slots__ = [
        # keys to transmit with i think
        '_n_keys',

        #
        "_managing_outgoing_partition"

    ]

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('N_KEYS', 1),
               ('KEYS', 2)])
    N_KEYS_REGION_SIZE = 4
    BYTES_PER_FIELD = 4

    # TODO FIND OUT WHY THIS MAX EXISTS?
    MAX_N_KEYS_SUPPORTED = 64
    TRANSFORM_SLICE_OUT = False

    def __init__(self, outgoing_partition):
        MachineVertex.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)

        self._managing_outgoing_partition = outgoing_partition

        transform = \
            self._managing_outgoing_partition.identifier\
            .transmission_parameter.full_transform(
                slice_out=self.TRANSFORM_SLICE_OUT)
        self._n_keys = transform.shape[0]

        # Check n keys size
        if self._n_keys > self.MAX_N_KEYS_SUPPORTED:
            raise NotImplementedError(
                "Connection is too wide to transmit to SpiNNaker. "
                "Consider breaking the connection up or making the "
                "originating node a function of time Node.")

    @overrides(AbstractProvidesNKeysForPartition.get_n_keys_for_partition)
    def get_n_keys_for_partition(self, partition, graph_mapper):
        if partition.identifier != self._managing_outgoing_partition:
            raise Exception("don't recognise this partition")
        else:
            return self._n_keys

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        return self.get_static_resources(self._n_keys)

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
        return SDPReceiverMachineVertex.BYTES_PER_FIELD * keys

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
        spec.switch_write_focus(self.DATA_REGIONS.KEYS.value)
        self._write_keys_region(routing_info)
        spec.end_specification()

    def _write_keys_region(self, routing_info):
        pass

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

    def send_output_to_spinnaker(self, value, placement, transceiver):
        # Apply the pre-slice, the connection function and the transform.
        c_value = value[self._pre_slice]

        # locate required transforms and functions
        partition_transmission_function = \
            self._managing_outgoing_partition.identifier\
                .transmission_parameter.function
        partition_transmission_transform = \
            self._managing_outgoing_partition.identifier\
                .transmission_parameter.full_transform(slice_out=False)

        # execute function if required
        if partition_transmission_function is not None:
            c_value = partition_transmission_function(c_value)

        # do transform
        c_value = numpy.dot(partition_transmission_transform, c_value)

        # create SCP packet
        # c_value is converted to S16.15
        data = helpful_functions.convert_numpy_array_to_s16_15(c_value)
        packet = SDPMessage(
            sdp_header=SDPHeader(
                destination_port=constants.SDP_PORTS.SDP_RECEIVER,
                destination_cpu=placement.p, destination_chip_x=placement.x,
                destination_chip_y=placement.y),
            data=data)
        transceiver.send_sdp_message(packet)
