"""
HeatDemoVertexPartitioned
"""

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

# spinnman imports
from spinnman.data.little_endian_byte_array_byte_reader import \
    LittleEndianByteArrayByteReader

# graph front end imports
from spynnaker_graph_front_end.abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex
from spynnaker_graph_front_end.utilities import utility_calls
# front end common imports
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions

# general imports
from enum import Enum
import struct
import hashlib

class GameOfLifeCell(
        PartitionedVertex, AbstractPartitionedDataSpecableVertex,
        AbstractProvidesOutgoingEdgeConstraints):
    """
    HeatDemoVertexPartitioned: a vertex peice for a heat demo.
    represnets a heat element.
    """

    # Regions for populations
    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('TIMINGS', 0),
               ('COMPONENTS', 1),
               ('TRANSMISSIONS', 2),
               ('STATE_REGION', 3),
               ('RECORDING_REGION', 4)])

    STATES = Enum(
        value="STATES",
        names=[('DEAD', 0),
               ('ALIVE', 1)])

    _model_based_max_atoms_per_core = 1
    _model_n_atoms = 1
    STATE_REGION_SIZE = 2 * 4
    TRANSMISSIONS_SIZE = 2 * 4

    def __init__(
            self, label, machine_time_step, time_scale_factor,
            initial_state=None,
            theshold_point=3, record_on_sdram=False, constraints=None):

        self._record_on_sdram = record_on_sdram

        PartitionedVertex.__init__(
            self, label=label, resources_required=None,
            constraints=constraints)
        AbstractPartitionedDataSpecableVertex.__init__(self)
        AbstractProvidesOutgoingEdgeConstraints.__init__(self)
        self._machine_time_step = machine_time_step
        self._time_scale_factor = time_scale_factor
        if initial_state is None:
            self._initial_state = self.STATES.DEAD
        elif isinstance(initial_state, self.STATES):
            self._initial_state = initial_state
        else:
            exceptions.ConfigurationException(
                "The intial state isnt recongised, please fix and try again")
        self._theshold_point = theshold_point

        # used to support 
        self._first_partitioned_edge = None

    @property
    def resources_required(self):
        """
        overriden method for getting the resource container.
        :return:
        """
        return ResourceContainer(cpu=CPUCyclesPerTickResource(45),
                                 dtcm=DTCMResource(34),
                                 sdram=self._calculate_sdram_usage())

    def get_binary_file_name(self):
        """

        :return:
        """
        return "life.aplx"

    def _calculate_sdram_usage(self):
        """
        returns the size of sdram required by the heat demo vertex.
        :return:
        """
        recording_size = 4  # one int for bool saying to record or not
        if self._record_on_sdram:
            recording_size = (self._no_machine_time_steps * 4) + 4
        total_sizes = (self.TRANSMISSIONS_SIZE +
                       constants.TIMINGS_REGION_BYTES +
                       (len(self._get_components()) * 4) + recording_size)
        return SDRAMResource(total_sizes)

    def model_name(self):
        """

        :return:
        """
        return "Game_Of_Life_Cell"

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

        self._write_timings_region_info(spec, self.DATA_REGIONS.TIMINGS.value)

        self._write_component_to_region(
            spec, self.DATA_REGIONS.COMPONENTS.value, self._get_components())

        self._write_tranmssion_keys(spec, routing_info, sub_graph)
        self._write_state_data(spec)
        self._write_recording_data(spec)
        # End-of-Spec:
        spec.end_specification()
        data_writer.close()

    def _write_recording_data(self, spec):
        spec.switch_write_focus(region=self.DATA_REGIONS.RECORDING_REGION.value)
        spec.comment("writing bool saying to record or not \n")
        if self._record_on_sdram:
            spec.write_value(data=1)
            spec.write_value(data=self._initial_state.value)
        else:
            spec.write_value(data=0)

    def _write_state_data(self, spec):
        spec.switch_write_focus(region=self.DATA_REGIONS.STATE_REGION.value)
        spec.comment("writing initial state for this game of life cell \n")
        spec.write_value(data=self._initial_state.value)
        spec.write_value(data=self._theshold_point)

    def _get_components(self):
        component_identifiers = list()
        component_identifiers.append(hashlib.md5("life").hexdigest()[:8])
        return component_identifiers

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
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TIMINGS.value,
            size=constants.TIMINGS_REGION_BYTES, label='timings')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.COMPONENTS.value,
            size=len(self._get_components()) * 4, label='components')
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.TRANSMISSIONS.value,
            size=self.TRANSMISSIONS_SIZE, label="keys")
        spec.reserve_memory_region(
            region=self.DATA_REGIONS.STATE_REGION.value,
            size=self.STATE_REGION_SIZE, label="state")
        if self._record_on_sdram:
            spec.reserve_memory_region(
                region=self.DATA_REGIONS.RECORDING_REGION.value,
                size=self._no_machine_time_steps * 4, label="recording_region")
        else:
            spec.reserve_memory_region(
                region=self.DATA_REGIONS.RECORDING_REGION.value,
                size=4, label="recording_region")

    def _write_timings_region_info(self, spec, region_id):
        """
        writes the timing configuration info including any constants expected
        by the c code on its configuration
        :param spec: the spec writer to write values to
        :param region_id: the region id to write these params to
        :return: None
        """

        # Write this to the timings region (to be picked up by the simulation):
        spec.switch_write_focus(region=region_id)
        spec.write_value(data=self._machine_time_step * self._timescale_factor)
        spec.write_value(data=self._no_machine_time_steps)

    def _write_component_to_region(self, spec, region_id, components):
        """
        writes the component magic numbers to a region for c code invesitgation.
        :param spec: the spec writer to write values to
        :param components: the iterable of identifiers
        :param region_id:  the region id to write these params to
        :return:None
        """

        # write these to a given region (to be picked up by the simulation)
        spec.switch_write_focus(region=region_id)
        for identifier in components:
            spec.write_value(data=identifier)

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

    def is_partitioned_data_specable(self):
        """
        helper method for isinstance
        :return:
        """
        return True

    def get_recorded_states(self, transciever, placement):
        """

        :param transciever:
        :param placement:
        :return:
        """
        if self._record_on_sdram:
            # Get the App Data for the core
            app_data_base_address = \
                transciever.get_cpu_information_from_core(
                    placement.x, placement.y, placement.p).user[0]

            # Get the position of the spike buffer
            recorded_state_region_base_address_offset = \
                utility_calls.get_region_base_address_offset(
                    app_data_base_address,
                    self.DATA_REGIONS.RECORDING_REGION.value)
            recorded_state_region_base_address_buf = \
                str(list(transciever.read_memory(
                    placement.x, placement.y,
                    recorded_state_region_base_address_offset, 4))[0])
            recorded_state_region_base_address = \
                struct.unpack("<I", recorded_state_region_base_address_buf)[0]
            recorded_state_region_base_address += app_data_base_address

            # read the recorded states
            recorded_states = transciever.read_memory_return_byte_array(
                placement.x, placement.y,
                recorded_state_region_base_address + 4,
                (self._no_machine_time_steps - 1) * 4)

            reader = LittleEndianByteArrayByteReader(recorded_states)
            data = list()
            while not reader.is_at_end():
                data.append(reader.read_int())
            return data
        else:
            return []