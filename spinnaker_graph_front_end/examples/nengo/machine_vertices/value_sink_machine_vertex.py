from enum import Enum

from pacman.model.graphs.machine import MachineVertex
from pacman.model.resources import ResourceContainer, SDRAMResource, \
    CPUCyclesPerTickResource, DTCMResource

from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from spinn_front_end_common.interface.buffer_management import \
    recording_utilities
from spinn_front_end_common.interface.buffer_management.buffer_models import \
    AbstractReceiveBuffersToHost
from spinn_front_end_common.interface.simulation import simulation_utilities
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities.utility_objs import ExecutableType

from spinn_utilities.overrides import overrides

from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_accepts_multicast_signals import AcceptsMulticastSignals


class ValueSinkMachineVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary,
        AcceptsMulticastSignals, AbstractReceiveBuffersToHost):

    __slots__ = [
        #
        '_input_slice'
    ]

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('SLICE_DATA', 1)
               ('FILTERS', 2),
               ('FILTER_ROUTING', 3),
               ('RECORDING', 4)])

    SLICE_DATA_SDRAM_REQUIREMENT = 8

    def __init__(self, input_slice):
        MachineVertex.__init__(self)
        MachineDataSpecableVertex.__init__(self)
        AbstractHasAssociatedBinary.__init__(self)
        AcceptsMulticastSignals.__init__(self)
        AbstractReceiveBuffersToHost.__init__(self)
        self._input_slice = input_slice

    @overrides(AcceptsMulticastSignals.accepts_multicast_signals)
    def accepts_multicast_signals(self, transmission_params):
        return transmission_params.projects_to(self._input_slice.as_slice)

    @overrides(MachineDataSpecableVertex.generate_machine_data_specification)
    def generate_machine_data_specification(
            self, spec, placement, machine_graph, routing_info, iptags,
            reverse_iptags, machine_time_step, time_scale_factor):

        self._reserve_memory_regions(spec)
        spec.switch_write_focus(self.DATA_REGIONS.SYSTEM.value)
        spec.write_array(simulation_utilities.get_simulation_header_array(
            self.get_binary_file_name(), machine_time_step,
            time_scale_factor))

        # data on slice, aka, input slice size and start point
        spec.switch_write_focus(self.DATA_REGIONS.SLICE_DATA.value)
        spec.write_value(self._input_slice.n_atoms)
        spec.write_array(self._input_slice.lo_atom)

        spec.switch_write_focus(self.DATA_REGIONS.FILTERS.value)

        filter_region, filter_routing_region = make_filter_regions(
            signals_conns, model.dt, True, model.keyspaces.filter_routing_tag)


        spec.end_specification()

    def _create_filter_data_region(self):
        signals_conns = model.get_signals_to_object(self)[InputPort.standard]
        filter_region, filter_routing_region = make_filter_regions(
            signals_conns, model.dt, True, model.keyspaces.filter_routing_tag)
        self._routing_region = filter_routing_region

    def _reserve_memory_regions(self, spec):
        spec.reserve_memory_region(
            self.DATA_REGIONS.SYSTEM.value(),
            constants.SYSTEM_BYTES_REQUIREMENT, label="system region")
        spec.reserve_memory_region(
            self.DATA_REGIONS.SLICE_DATA.value(),
            XXXXXXX, label="filter region")
        spec.reserve_memory_region(
            self.DATA_REGIONS.ROUTING.value(),
            XXXXXXXX,
            label="routing region")

    @overrides(AbstractHasAssociatedBinary.get_binary_start_type)
    def get_binary_start_type(self):
        return ExecutableType.USES_SIMULATION_INTERFACE

    @property
    @overrides(MachineVertex.resources_required, )
    def resources_required(self, n_machine_time_steps):
        container = ResourceContainer(
            sdram=SDRAMResource(
                constants.SYSTEM_BYTES_REQUIREMENT +
                ValueSinkMachineVertex.SLICE_DATA_SDRAM_REQUIREMENT),
            dtcm=DTCMResource(0),
            cpu_cycles=CPUCyclesPerTickResource(0))

        recording_sizes = recording_utilities.get_recording_region_sizes(
            self._get_buffered_sdram(self._input_slice, n_machine_time_steps),
            self._minimum_buffer_sdram, self._maximum_sdram_for_buffering,
            self._using_auto_pause_and_resume)
        container.extend(recording_utilities.get_recording_resources(
            recording_sizes, self._receive_buffer_host,
            self._receive_buffer_port))

    @overrides(AbstractReceiveBuffersToHost.get_minimum_buffer_sdram_usage)
    def get_minimum_buffer_sdram_usage(self):
        pass

    @overrides(AbstractReceiveBuffersToHost.get_recording_region_base_address)
    def get_recording_region_base_address(self, txrx, placement):
        pass

    @overrides(AbstractReceiveBuffersToHost.get_recorded_region_ids)
    def get_recorded_region_ids(self):
        pass

    @overrides(AbstractReceiveBuffersToHost.get_n_timesteps_in_buffer_space)
    def get_n_timesteps_in_buffer_space(self, buffer_space, machine_time_step):
        pass

    @overrides(AbstractHasAssociatedBinary.get_binary_file_name)
    def get_binary_file_name(self):
        return "value_sink.aplx"
