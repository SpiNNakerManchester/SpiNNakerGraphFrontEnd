"""
HeatDemoVertexPartitioned
"""

# heat demo imports
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
from spynnaker_graph_front_end.abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex

# front end common imports
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions
from spinn_front_end_common.abstract_models.\
    abstract_provides_outgoing_edge_constraints\
    import AbstractProvidesOutgoingEdgeConstraints

# general imports
from enum import Enum


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
               ('NEIGBOUR_DATA', 2)])
    # one key for each incoming edge.
    NEIGBOUR_DATA_SIZE = 6 * 4
    TRANSMISSION_DATA_SIZE = 2 * 4

    _model_based_max_atoms_per_core = 1
    _model_n_atoms = 1

    def __init__(self, label, machine_time_step, time_scale_factor,
                 constraints=None):

        # resoruces used by a heat element vertex
        resoruces = ResourceContainer(cpu=CPUCyclesPerTickResource(45),
                                      dtcm=DTCMResource(34),
                                      sdram=SDRAMResource(23))

        PartitionedVertex.__init__(
            self, label=label, resources_required=resoruces,
            constraints=constraints)
        AbstractPartitionedDataSpecableVertex.__init__(self)
        AbstractProvidesOutgoingEdgeConstraints.__init__(self)
        self._machine_time_step = machine_time_step
        self._time_scale_factor = time_scale_factor

    def get_binary_file_name(self):
        """

        :return:
        """
        return "heat_demo.aplx"

    @staticmethod
    def model_name():
        """

        :return:
        """
        return "Heat_Demo_Vertex"

    def get_outgoing_edge_constraints(self, partitioned_edge, graph_mapper):
        constraints = list()
        constraints.append(KeyAllocatorSameKeysConstraint(partitioned_edge))
        return constraints

    def generate_data_spec(
            self, placement, sub_graph, routing_info, hostname, report_folder,
            write_text_specs, application_run_time_folder):
        """

        :param placement:
        :param sub_graph:
        :param routing_info:
        :param hostname:
        :param report_folder:
        :param write_text_specs:
        :param application_run_time_folder:
        :return:
        """
        data_writer, report_writer = \
            self.get_data_spec_file_writers(
                placement.x, placement.y, placement.p, hostname, report_folder,
                write_text_specs, application_run_time_folder)

        spec = DataSpecificationGenerator(data_writer, report_writer)
        # Setup words + 1 for flags + 1 for recording size
        setup_size = (constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 2) * 4

        spec.comment("\n*** Spec for SpikeSourceArray Instance ***\n\n")

        # ###################################################################
        # Reserve SDRAM space for memory areas:

        spec.comment("\nReserving memory space for spike data region:\n\n")

        # Create the data regions for the spike source array:
        self._reserve_memory_regions(spec, setup_size)
        self._write_basic_setup_info(spec, self.CORE_APP_IDENTIFIER,
                                     self.DATA_REGIONS.SYSTEM_REGION.value)
        self._write_tranmssion_keys(spec, routing_info, sub_graph)
        self._write_input_keys(spec, routing_info, sub_graph)
        # End-of-Spec:
        spec.end_specification()
        data_writer.close()

    def _reserve_memory_regions(self, spec, system_size):
        """
        *** Modified version of same routine in abstract_models.py These could
        be combined to form a common routine, perhaps by passing a list of
        entries. ***
        Reserve memory for the system, indices and spike data regions.
        The indices region will be copied to DTCM by the executable.
        :param spec:
        :param system_size:
        :return:
        """
        spec.reserve_memory_region(region=self.DATA_REGIONS.SYSTEM_REGION.value,
                                   size=system_size, label='systemInfo')
        spec.reserve_memory_region(region=self.DATA_REGIONS.TRANSMISSIONS.value,
                                   size=self.TRANSMISSION_DATA_SIZE,
                                   label="inputs")
        spec.reserve_memory_region(region=self.DATA_REGIONS.NEIGBOUR_DATA.value,
                                   size=self.NEIGBOUR_DATA_SIZE, label="inputs")

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
        spec.write_value(data=self._machine_time_step * self._timescale_factor)
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

    def _write_input_keys(self, spec, routing_info, sub_graph):
        """

        :param spec:
        :param routing_info:
        :param sub_graph:
        :return:
        """
        spec.switch_write_focus(region=self.DATA_REGIONS.NEIGBOUR_DATA.value)
        # get incoming edges
        incoming_edges = sub_graph.incoming_subedges_from_subvertex(self)
        sorted(incoming_edges, key=lambda subedge: subedge.direction,
               reverse=True)
        # write each key that this modle should expect packets from.
        current_direction = 0
        for edge in incoming_edges:
            if not isinstance(edge, HeatDemoEdge):
                raise exceptions.ConfigurationException(
                    "The edge connected to this model is not reconisable as a"
                    "heat element. This is deemed as an error")
            else:
                if edge.direction.value != current_direction:
                    spec.write_value(data=0)
                else:
                    keys_and_masks = \
                        routing_info.get_keys_and_masks_from_subedge(edge)
                    key = keys_and_masks[0][0].key
                    spec.write_value(data=key)
                current_direction += 1