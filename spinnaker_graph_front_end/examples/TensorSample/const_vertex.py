import logging
import struct
from enum import Enum
from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spinn_front_end_common.utilities.utility_objs import ExecutableType
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_utilities.overrides import overrides
from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models.impl import (MachineDataSpecableVertex)
from spinn_front_end_common.utilities.constants import DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES
from pacman.executor.injection_decorator import inject_items
from pacman.utilities.utility_calls import is_single
from spinn_front_end_common.utilities.helpful_functions import (
    locate_memory_region_for_placement, read_config_int)
from pacman.model.resources import (ResourceContainer, ConstantSDRAM)

logger = logging.getLogger(__name__)


class ConstVertex(MachineVertex,
                  AbstractHasAssociatedBinary,
                  MachineDataSpecableVertex):

    TRANSMISSION_DATA_SIZE = 2 * 4 # has key and key
    INPUT_DATA_SIZE = 4 # constant int number
    RECORDING_DATA_SIZE = 4

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('TRANSMISSIONS', 0),
               ('INPUT', 1),
               ('RECORDING_CONST_VALUES', 2)])

    PARTITION_ID = "ADDITION_PARTITION"

    def __init__(self, label, constValue):
        MachineVertex.__init__(self, )
        AbstractHasAssociatedBinary.__init__(self)
        MachineDataSpecableVertex.__init__(self)

        print("\n const_vertex init")

        self._constant_data_size = 4
        self.placement = None
        # app specific elements
        self._constValue = constValue
        self._label = label
        print("const_value in the instance :",self._constValue)

    def _reserve_memory_regions(self, spec):
        print("\n const_vertex _reserve_memory_regions")

        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSION_DATA_SIZE, label="keys")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.INPUT.value,
            size=self.INPUT_DATA_SIZE, label="input_const_values")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.RECORDING_CONST_VALUES.value,
            size=self.RECORDING_DATA_SIZE)

    @inject_items({"data_n_time_steps": "DataNTimeSteps"})
    @overrides(
        MachineDataSpecableVertex.generate_machine_data_specification,
        additional_arguments={"data_n_time_steps"})
    def generate_machine_data_specification(self, spec, placement, machine_graph,
                                            routing_info, iptags, reverse_iptags,
                                            machine_time_step, time_scale_factor, data_n_time_steps):
        print("\n const_vertex generate_machine_data_specification")

        self.placement = placement
        # reserve memory region
        self._reserve_memory_regions(spec)

        # check got right number of keys and edges going into me
        partitions = \
            machine_graph.get_outgoing_edge_partitions_starting_at_vertex(self)

        print("const_partitions :", partitions)
        if not is_single(partitions):
            raise ConfigurationException(
                "Can only handle one type of partition.")

        ## check for duplicates
        edges = list(machine_graph.get_edges_ending_at_vertex(self))
        print("edges : ", edges)
        # if len(edges) != 8:
        #     raise ConfigurationException(
        #         "I've not got the right number of connections. I have {} "
        #         "instead of 8".format(
        #             len(machine_graph.get_edges_ending_at_vertex(self))))
        print(len(machine_graph.get_edges_ending_at_vertex(self)))
        for edge in edges:
            if edge.pre_vertex == self:
                raise ConfigurationException(
                    "I'm connected to myself, this is deemed an error"
                    " please fix.")

        # write key needed to transmit with
        key = routing_info.get_first_key_from_pre_vertex(
            self, self.PARTITION_ID)
        print("\n key is ", key)
        spec.switch_write_focus(
            region=self.DATA_REGIONS.TRANSMISSIONS.value)
        spec.write_value(0 if key is None else 1)
        spec.write_value(0 if key is None else key)

        # write constant value
        spec.switch_write_focus(self.DATA_REGIONS.INPUT.value)
        print("\n write constant value ", self._constValue)
        spec.write_value(self._constValue)

        # End-of-Spec:
        spec.end_specification()

    @property
    @overrides(MachineVertex.resources_required)
    def resources_required(self):
        print("\n {} resources_required".format(self._label))

        fixed_sdram = (self.TRANSMISSION_DATA_SIZE + self.INPUT_DATA_SIZE + self.RECORDING_DATA_SIZE +
                       DATA_SPECABLE_BASIC_SETUP_INFO_N_BYTES)

        print("fixed_sdram : ",fixed_sdram)
        return ResourceContainer(sdram=ConstantSDRAM(fixed_sdram))

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        print("\n const_vertex get_binary_file_name")

        return "tensorFlow_const.aplx"

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.SYNC

    def get_minimum_buffer_sdram_usage(self):
        return self._constant_data_size


    def get_recorded_region_ids(self):
        return [0]

    def get_recording_region_base_address(self, txrx, placement):
        return locate_memory_region_for_placement(
            placement, self.DATA_REGIONS.RECORDING.value, txrx)
