# pacman imports
from collections import OrderedDict
from pacman.executor.injection_decorator import inject_items
from pacman.model.decorators.overrides import overrides
from pacman.model.graphs.application.impl.application_vertex import \
    ApplicationVertex
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.sdram_resource import SDRAMResource
from spinn_front_end_common.abstract_models.abstract_binary_uses_simulation_run import \
    AbstractBinaryUsesSimulationRun
from spinn_front_end_common.utilities import constants

# spinn front end common imports
from spinn_front_end_common.interface.buffer_management.buffer_models.\
    receives_buffers_to_host_basic_impl import \
    ReceiveBuffersToHostBasicImpl

# GFE imports
from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_machine_cells import ConwaysMachineCells
from spinnaker_graph_front_end.examples.Conways.q_partitionable.\
    conways_synapse_types import \
    ConwaysSynapseTypes
from spinnaker_graph_front_end.utilities.conf import config

# general imports
from enum import Enum
import struct

# hacked bits
from spynnaker.pyNN.models.neuron.synaptic_manager import SynapticManager


class ConwaysApplicationGrid(
        ApplicationVertex, ReceiveBuffersToHostBasicImpl,
        AbstractBinaryUsesSimulationRun):
    """ Cell which represents a cell within the 2d fabric
    """

    BASIC_MALLOC_USAGE = 5

    def __init__(self, grid_size_x, grid_size_y, active_states, label):

        ReceiveBuffersToHostBasicImpl.__init__(self)
        AbstractBinaryUsesSimulationRun.__init__(self)

        self._grid_size_x = grid_size_x
        self._grid_size_y = grid_size_y

        # activate the buffer out functionality
        self.activate_buffering_output(
            minimum_sdram_for_buffering=(
                config.getint("Buffers", "minimum_buffer_sdram")
            ),
            buffered_sdram_per_timestep=4)

        ApplicationVertex.__init__(self, label)

        # app specific data items
        self._states_by_index = list()
        for x in range(0, grid_size_x):
            for y in range(0, grid_size_y):
                if (x, y) in active_states:
                    self._states_by_index.append(True)
                else:
                    self._states_by_index.append(False)

        self._mapping_data = SynapticManager(
            ConwaysSynapseTypes(self._states_by_index), 0, 8)

    @property
    @overrides(ApplicationVertex.n_atoms)
    def n_atoms(self):
        return len(self._states_by_index)

    def get_state_by_grid_coord(self, x, y):
        index = x + (y * self._grid_size_y)
        return self._states_by_index[index]

    def get_state_by_index(self, index):
        return self._states_by_index[index]

    def get_data(self, buffer_manager, machine_graph, placements, graph_mapper):
        data = OrderedDict()

        # extract for every conways basic cell
        for machine_vertex in machine_graph.vertices:
            if isinstance(machine_vertex, ConwaysMachineCells):
                placement = placements.get_placement_of_vertex(machine_vertex)

            # for buffering output info is taken form the buffer manager
            reader, data_missing = \
                buffer_manager.get_data_for_vertex(
                    placement, ConwaysMachineCells.DATA_REGIONS.RESULTS.value,
                    ConwaysMachineCells.DATA_REGIONS.
                    BUFFERED_STATE_REGION.value)

            # do check for missing data
            if data_missing:
                print "missing_data from ({}, {}, {}); ".format(
                    placement.x, placement.y, placement.p)

            # get raw data
            raw_data = reader.read_all()

            elements = struct.unpack(
                "<{}I".format(len(raw_data) / 4), str(raw_data))

            time = 0
            vertex_slice = graph_mapper.get_slice(machine_vertex)
            current_cell = vertex_slice.lo_atom
            for element in elements:
                # if first cell, make new time slow
                if current_cell == 0 and time not in data:
                    data[time] = dict()
                x = current_cell % self._grid_size_y
                y = current_cell / self._grid_size_y
                if element == 0:
                    data[time][(x, y)] = False
                else:
                    data[time][(x, y)] = True

                # if last cell, reset for new time set
                if current_cell == vertex_slice.hi_atom:
                    time += 1
                    current_cell = vertex_slice.lo_atom
                else:
                    current_cell += 1

        # return the data
        return data

    def create_machine_vertex(self, vertex_slice, resources_required,
                              label=None, constraints=None):

        # filter states for the subsection
        sub_states = list()
        for sub_state in range(vertex_slice.lo_atom, vertex_slice.hi_atom):
            sub_states.append(self._states_by_index[sub_state])

        # create mapping between app space and atoms id
        coords = list()
        for atom_id in range(vertex_slice.lo_atom, vertex_slice.hi_atom):
            coords.append(int(atom_id % self._grid_size_y))
        for atom_id in range(vertex_slice.lo_atom, vertex_slice.hi_atom):
            coords.append(int(atom_id / self._grid_size_y))

        # build machine vertex
        return ConwaysMachineCells(
            vertex_slice, resources_required,
            label="Cells {} to {}".format(
                vertex_slice.lo_atom, vertex_slice.hi_atom),
            synaptic_manager=self._mapping_data, coords=coords)

    @inject_items({
        "graph": "MemoryApplicationGraph",
        "machine_time_step": "MachineTimeStep"
    })
    @overrides(
        ApplicationVertex.get_resources_used_by_atoms,
        additional_arguments={
            "graph", "machine_time_step"
        }
    )
    def get_resources_used_by_atoms(
            self, vertex_slice, graph, machine_time_step):
        return ResourceContainer(
            sdram=SDRAMResource(
                self._calculate_sdram_requirement(
                    vertex_slice, graph, machine_time_step)),
            cpu_cycles=CPUCyclesPerTickResource(
                self._calculate_cpu_cycles(vertex_slice)),
            dtcm=DTCMResource(
                self._calculate_dtcm_usage(vertex_slice)))

    def _calculate_sdram_requirement(
            self, vertex_slice, graph, machine_time_step):
        return \
            (constants.SYSTEM_BYTES_REQUIREMENT +
             ConwaysMachineCells.TRANSMISSION_DATA_SIZE +
             (ConwaysMachineCells.STATE_DATA_SIZE * vertex_slice.n_atoms) +
             (ConwaysMachineCells.NEIGHBOUR_INITIAL_STATES_SIZE *
              vertex_slice.n_atoms) +
             self._mapping_data.get_sdram_usage_in_bytes(
                 vertex_slice, graph.get_edges_ending_at_vertex(self),
                 machine_time_step) +
             constants.MAX_SIZE_OF_BUFFERED_REGION_ON_CHIP +
             ReceiveBuffersToHostBasicImpl.get_buffer_state_region_size(1) +
             (self._get_number_of_mallocs_used_by_dsg() *
              constants.SARK_PER_MALLOC_SDRAM_USAGE) +
             (ConwaysMachineCells.COORDS_PER_CELL_COST * vertex_slice.n_atoms))

    def _get_number_of_mallocs_used_by_dsg(self):
        return (
            self.BASIC_MALLOC_USAGE +
            self._mapping_data.get_number_of_mallocs_used_by_dsg())

    @staticmethod
    def _calculate_dtcm_usage(vertex_slice):
        return 5 * vertex_slice.n_atoms

    @staticmethod
    def _calculate_cpu_cycles(vertex_slice):
        return 200 * vertex_slice.n_atoms

    def get_connections_from_machine(
            self, transceiver, placement, edge, graph_mapper,
            routing_infos, synapse_info, machine_time_step):
        return self._mapping_data.get_connections_from_machine(
            transceiver, placement, edge, graph_mapper,
            routing_infos, synapse_info, machine_time_step)

    def __repr__(self):
        return self._label
