"""
HeatDemoVertexPartitioned
"""

# heat demo imports
from data_specification.enums.data_type import DataType
from examples.heat_demo.heat_demo_command_edge import HeatDemoCommandEdge
from examples.heat_demo.heat_demo_edge import HeatDemoEdge

# data spec imports
from data_specification.data_specification_generator import \
    DataSpecificationGenerator

# pacman imports
from pacman.model.constraints.key_allocator_constraints.\
    key_allocator_same_keys_constraint import \
    KeyAllocatorSameKeysConstraint
from pacman.model.partitioned_graph.partitioned_vertex import PartitionedVertex
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.sdram_resource import SDRAMResource

# graph front end imports
from spinn_front_end_common.abstract_models.\
    abstract_provides_outgoing_edge_constraints import \
    AbstractProvidesOutgoingEdgeConstraints
from spinn_front_end_common.utility_models.live_packet_gather import \
    LivePacketGather
from spinn_front_end_common.utility_models.\
    reverse_ip_tag_multi_cast_source import ReverseIpTagMultiCastSource
from spynnaker_graph_front_end.abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex
from spynnaker_graph_front_end.utilities import utility_calls

# front end common imports
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions

# general imports
from enum import Enum
import struct
import numpy


class HeatDemoVertexPartitioned(
        PartitionedVertex, AbstractPartitionedDataSpecableVertex,
        AbstractProvidesOutgoingEdgeConstraints):
    """
    HeatDemoVertexPartitioned: a vertex peice for a heat demo.
    represnets a heat element.
    """

    CORE_APP_IDENTIFIER = 0xABCD

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('NEIGBOUR_KEYS', 2),
               ('COMMAND_KEYS', 3),
               ('OUPUT_KEY', 4),
               ('TEMP_VALUE', 5),
               ('RECORDING_REGION', 6)])

    # one key for each incoming edge.
    NEIGBOUR_DATA_SIZE = 10 * 4
    TRANSMISSION_DATA_SIZE = 2 * 4
    COMMAND_KEYS_SIZE = 3 * 4
    OUPUT_KEY_SIZE = 1 * 4
    TEMP_VALUE_SIZE = 1 * 4

    _model_based_max_atoms_per_core = 1
    _model_n_atoms = 1

    def __init__(self, label, machine_time_step, time_scale_factor,
                 heat_tempature=0, record_on_sdram=False, constraints=None):

        self._record_on_sdram = record_on_sdram

        PartitionedVertex.__init__(
            self, label=label, resources_required=None,
            constraints=constraints)
        AbstractPartitionedDataSpecableVertex.__init__(self)
        AbstractProvidesOutgoingEdgeConstraints.__init__(self)
        self._machine_time_step = machine_time_step
        self._time_scale_factor = time_scale_factor
        self._heat_temperature = heat_tempature

        # used to support 
        self._first_partitioned_edge = None

    @property
    def resources_required(self):
        return ResourceContainer(cpu=CPUCyclesPerTickResource(45),
                                 dtcm=DTCMResource(34),
                                 sdram=self._calculate_sdram_usage())

    def get_binary_file_name(self):
        """

        :return:
        """
        return "heat_demo.aplx"

    def _calculate_sdram_usage(self):
        """
        returns the size of sdram required by the heat demo vertex.
        :return:
        """
        main_mem_regions_sizes = (
            self.TRANSMISSION_DATA_SIZE + self.NEIGBOUR_DATA_SIZE +
            self.COMMAND_KEYS_SIZE + self.TEMP_VALUE_SIZE + self.OUPUT_KEY_SIZE)
        system_size = (constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 2) * 4
        recording_size = 4  # one int for bool saying to record or not
        if self._record_on_sdram:
            recording_size = (self._no_machine_time_steps * 4) + 4
        total_sizes = main_mem_regions_sizes + system_size + recording_size
        return SDRAMResource(total_sizes)

    def model_name(self):
        """

        :return:
        """
        return "Heat_Demo_Vertex"

    def get_outgoing_edge_constraints(self, partitioned_edge, graph_mapper):
        """

        :param partitioned_edge:
        :param graph_mapper:
        :return:
        """
        if self._first_partitioned_edge is None:
            self._first_partitioned_edge = partitioned_edge
            return list()
        else:
            constraints = list()
            constraints.append(KeyAllocatorSameKeysConstraint(
                self._first_partitioned_edge))
            return constraints

    def generate_data_spec(
            self, placement, sub_graph, routing_info, hostname, report_folder,
            ip_tags, reverse_ip_tags, write_text_specs,
            application_run_time_folder):
        """
        method to determine how to generate their data spec for a non neural
        application

        :param placement: the placement object for the dsg
        :param sub_graph: the partitioned graph object for this dsg
        :param routing_info: the routing info object for this dsg
        :param hostname: the machines hostname
        :param ip_tags: the collection of iptags generated by the tag allcoator
        :param reverse_ip_tags: the colelction of reverse iptags generated by
        the tag allcoator
        :param report_folder: the folder to write reports to
        :param write_text_specs: bool which says if test specs should be written
        :param application_run_time_folder: the folder where application files
         are written
        """
        data_writer, report_writer = \
            self.get_data_spec_file_writers(
                placement.x, placement.y, placement.p, hostname, report_folder,
                write_text_specs, application_run_time_folder)

        spec = DataSpecificationGenerator(data_writer, report_writer)

        spec.comment("\n*** Spec for SpikeSourceArray Instance ***\n\n")

        # ###################################################################
        # Reserve SDRAM space for memory areas:

        spec.comment("\nReserving memory space for spike data region:\n\n")

        # Create the data regions for the spike source array:
        self._reserve_memory_regions(spec)
        self._write_basic_setup_info(spec, self.CORE_APP_IDENTIFIER,
                                     self.DATA_REGIONS.SYSTEM.value)
        self._write_tranmssion_keys(spec, routing_info, sub_graph)
        self._write_key_data(spec, routing_info, sub_graph)
        self._write_temp_data(spec)
        self._write_recording_data(spec)
        # End-of-Spec:
        spec.end_specification()
        data_writer.close()

    def _write_recording_data(self, spec):
        spec.switch_write_focus(region=self.DATA_REGIONS.RECORDING_REGION.value)
        spec.comment("writing bool saying to record or not \n")
        if self._record_on_sdram:
            spec.write_value(data=1)
        else:
            spec.write_value(data=0)

    def _write_temp_data(self, spec):
        spec.switch_write_focus(region=self.DATA_REGIONS.TEMP_VALUE.value)
        spec.comment("writing initial temp for this heat element \n")
        spec.write_value(data=self._heat_temperature)

    def _reserve_memory_regions(self, spec):
        """
        *** Modified version of same routine in abstract_models.py These could
        be combined to form a common routine, perhaps by passing a list of
        entries. ***
        Reserve memory for the system, indices and spike data regions.
        The indices region will be copied to DTCM by the executable.
        :param spec:
        :return:
        """
        # Setup words + 1 for flags + 1 for recording size
        system_size = (constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 2) * 4
        spec.reserve_memory_region(region=self.DATA_REGIONS.SYSTEM.value,
                                   size=system_size, label='systemInfo')
        spec.reserve_memory_region(region=self.DATA_REGIONS.TRANSMISSIONS.value,
                                   size=self.TRANSMISSION_DATA_SIZE,
                                   label="inputs")
        spec.reserve_memory_region(region=self.DATA_REGIONS.NEIGBOUR_KEYS.value,
                                   size=self.NEIGBOUR_DATA_SIZE, label="inputs")
        spec.reserve_memory_region(region=self.DATA_REGIONS.COMMAND_KEYS.value,
                                   size=self.COMMAND_KEYS_SIZE,
                                   label="commands")
        spec.reserve_memory_region(region=self.DATA_REGIONS.OUPUT_KEY.value,
                                   size=self.OUPUT_KEY_SIZE, label="outputs")
        spec.reserve_memory_region(region=self.DATA_REGIONS.TEMP_VALUE.value,
                                   size=self.TEMP_VALUE_SIZE, label="temp")
        if self._record_on_sdram:
            spec.reserve_memory_region(
                region=self.DATA_REGIONS.RECORDING_REGION.value,
                size=self._no_machine_time_steps * 4, label="reocrding_region")
        else:
            spec.reserve_memory_region(
                region=self.DATA_REGIONS.RECORDING_REGION.value,
                size=4, label="reocrding_region")

    def _write_basic_setup_info(self, spec, core_app_identifier, region_id):
        """
         Write this to the system region (to be picked up by the simulation):
        :param spec:
        :param core_app_identifier:
        :param region_id:
        :return:
        """
        spec.switch_write_focus(region=region_id)
        spec.write_value(data=core_app_identifier)
        spec.write_value(data=self._machine_time_step * self._time_scale_factor)
        spec.write_value(data=self._no_machine_time_steps)

    def _write_tranmssion_keys(self, spec, routing_info, subgraph):
        """

        :param spec:
        :param routing_info:
        :param subgraph:
        :return:
        """
        # Every subedge should have the same key
        keys_and_masks = routing_info.get_keys_and_masks_from_subedge(
            subgraph.outgoing_subedges_from_subvertex(self)[0])
        key = keys_and_masks[0].key
        spec.switch_write_focus(region=self.DATA_REGIONS.TRANSMISSIONS.value)
        # Write Key info for this core:
        if key is None:
            # if theres no key, then two falses will cover it.
            spec.write_value(data=0)
            spec.write_value(data=0)
        else:
            # has a key, thus set has key to 1 and then add key
            spec.write_value(data=1)
            spec.write_value(data=key)

    def _write_key_data(self, spec, routing_info, sub_graph):
        """

        :param spec:
        :param routing_info:
        :param sub_graph:
        :return:
        """
        spec.switch_write_focus(region=self.DATA_REGIONS.NEIGBOUR_KEYS.value)
        # get incoming edges
        incoming_edges = sub_graph.incoming_subedges_from_subvertex(self)
        spec.comment("\n the keys for the neighbours in EAST, NORTH, WEST, "
                     "SOUTH. order:\n\n")
        direction_edges = list()
        fake_temp_edges = list()
        command_edge = None
        output_edge = None
        for incoming_edge in incoming_edges:
            if (isinstance(incoming_edge, HeatDemoEdge) and
                    isinstance(incoming_edge.pre_subvertex,
                               ReverseIpTagMultiCastSource)):
                fake_temp_edges.append(incoming_edge)
            elif (isinstance(incoming_edge, HeatDemoEdge) and 
                    isinstance(incoming_edge.pre_subvertex,
                               HeatDemoVertexPartitioned)):
                direction_edges.append(incoming_edge)
            elif isinstance(incoming_edge, HeatDemoCommandEdge):
                if command_edge is not None:
                    raise exceptions.ConfigurationException(
                        "cant have more than one command edge. Error!")
                command_edge = incoming_edge

        out_going_edges = sub_graph.outgoing_subedges_from_subvertex(self)
        for out_going_edge in out_going_edges:
            if isinstance(out_going_edge.post_subvertex, LivePacketGather):
                if output_edge is not None:
                    raise exceptions.ConfigurationException(
                        "already found a outgoing edge."
                        " cant have more than one!")
                output_edge = out_going_edge

        direction_edges = \
            sorted(direction_edges, key=lambda subedge: subedge.direction.value,
                   reverse=False)

        # write each key that this modle should expect packets from in order
        # of EAST, NORTH, WEST, SOUTH.
        loaded_keys = 0
        for current_direction in range(4):
            written = False
            for edge in direction_edges:
                if edge.direction.value == current_direction:
                    keys_and_masks = \
                        routing_info.get_keys_and_masks_from_subedge(edge)
                    key = keys_and_masks[0].key
                    spec.write_value(data=key)
                    loaded_keys += 1
                    written = True
            if not written:
                spec.write_value(data_type=DataType.INT32, data=-1)

        if loaded_keys == 0:
            raise exceptions.ConfigurationException(
                "This heat element  {} does not receive any data from other "
                "elements. Please fix and try again.\n It currently has "
                "incoming edges of {}\n directional edges of {}\n and fake "
                "edges of {}\n and command edge of {}\n and output edge of {}"
                .format(self.label, incoming_edges, direction_edges,
                        fake_temp_edges, command_edge, output_edge))

        # write each key that this model should expect packets from in order of
        # EAST, NORTH, WEST, SOUTH for injected temps
        fake_temp_edges = \
            sorted(fake_temp_edges, key=lambda subedge: subedge.direction.value,
                   reverse=False)

        for current_direction in range(4):
            written = False
            for edge in fake_temp_edges:
                if edge.direction.value == current_direction:
                    keys_and_masks = \
                        routing_info.get_keys_and_masks_from_subedge(edge)
                    key = keys_and_masks[0].key
                    spec.write_value(data=key)
                    written = True
            if not written:
                spec.write_value(data_type=DataType.INT32, data=-1)

        # write key for host output
        spec.switch_write_focus(region=self.DATA_REGIONS.OUPUT_KEY.value)
        spec.comment("\n the key for transmitting temp to host gatherer:\n\n")
        if output_edge is not None:
            output_edge_key_and_mask = \
                routing_info.get_keys_and_masks_from_subedge(output_edge)
            key = output_edge_key_and_mask[0].key
            spec.write_value(data=key)
        else:
            spec.write_value(data_type=DataType.INT32, data=-1)

        # write keys for commands
        spec.switch_write_focus(region=self.DATA_REGIONS.COMMAND_KEYS.value)
        spec.comment("\n the command keys in order of STOP, PAUSE, RESUME:\n\n")
        commands_keys_and_masks = \
            routing_info.get_keys_and_masks_from_subedge(command_edge)

        # get just the keys
        keys = list()
        for key_and_mask in commands_keys_and_masks:
            keys_given, _ = key_and_mask.get_keys(n_keys=3)
            keys.extend(keys_given)

        # sort keys in assending order
        keys = sorted(keys, reverse=False)
        if len(keys) != 3:
            raise exceptions.ConfigurationException(
                "Do not have enough keys to reflect the commands. broken."
                "There are {} keys instead of 3".format(len(keys)))
        for key in keys:
            spec.write_value(data=key)

    def is_partitioned_data_specable(self):
        """
        helper method for isinstance
        :return:
        """
        return True

    def get_recorded_temperatures(self, transciever, placement):
        """

        :param transciever:
        :return:
        """
        if self._record_on_sdram:
            # Get the App Data for the core
            app_data_base_address = \
                transciever.get_cpu_information_from_core(
                    placement.x, placement.y, placement.p).user[0]

            # Get the position of the spike buffer

            recorded_temp_region_base_address_offset = \
                utility_calls.get_region_base_address_offset(
                    app_data_base_address,
                    self.DATA_REGIONS.RECORDING_REGION.value)
            recorded_temp_region_base_address_buf = \
                str(list(transciever.read_memory(
                    placement.x, placement.y,
                    recorded_temp_region_base_address_offset, 4))[0])
            recorded_temp_region_base_address = \
                struct.unpack("<I", recorded_temp_region_base_address_buf)[0]
            recorded_temp_region_base_address += app_data_base_address

            # read the recorded temps
            recorded_temps = transciever.read_memory(
                placement.x, placement.y, recorded_temp_region_base_address + 4,
                self._no_machine_time_steps * 4)

            data_list = bytearray()
            for data in recorded_temps:
                data_list.extend(data)
            numpy_data = numpy.asarray(data_list, dtype="uint8")
            return numpy_data
        else:
            return []