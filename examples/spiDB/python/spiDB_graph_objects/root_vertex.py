
from pacman.model.partitioned_graph.partitioned_vertex import PartitionedVertex
from pacman.model.resources.cpu_cycles_per_tick_resource import \
    CPUCyclesPerTickResource
from pacman.model.constraints.placer_constraints\
    .placer_chip_and_core_constraint import PlacerChipAndCoreConstraint
from pacman.model.resources.dtcm_resource import DTCMResource
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.sdram_resource import SDRAMResource
from pacman.model.constraints.tag_allocator_constraints \
    .tag_allocator_require_reverse_iptag_constraint \
    import TagAllocatorRequireReverseIptagConstraint

from spinn_front_end_common.abstract_models.\
    abstract_partitioned_data_specable_vertex \
    import AbstractPartitionedDataSpecableVertex
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.abstract_models.\
    abstract_provides_outgoing_partition_constraints \
    import AbstractProvidesOutgoingPartitionConstraints
from spinn_front_end_common.utilities import exceptions

from spinnaker_graph_front_end.utilities.conf import config

from data_specification.data_specification_generator import \
    DataSpecificationGenerator

from enum import Enum

import logging

logger = logging.getLogger(__name__)

MODES = Enum(
    value="MODES",
    names=[("KEY_VALUE", 0),
           ("RELATIONAL", 1),
           ("BOTH", 2)])


class RootVertex(PartitionedVertex, AbstractPartitionedDataSpecableVertex):
    """
    vertex that does the communication work for all stuff on a chip.
    """

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('SDP_PORT', 2),
               ('STRING_DATA', 3)])

    STRING_DATA_SIZE = 7000000
    SDP_REGION_SIZE = 4
    TRANSMISSION_SIZE = 8

    def __init__(
            self, label, port, placement, machine_time_step=None,
            time_scale_factor=None, constraints=None, board_address=None,
            sdp_port=4, tag=None, mode=MODES.KEY_VALUE.value):

        system_region_size = \
            (constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS + 3) * 4
        sdram_requirements = \
            system_region_size + self.TRANSMISSION_SIZE + \
            self.SDP_REGION_SIZE + self.STRING_DATA_SIZE

        resources = ResourceContainer(cpu=CPUCyclesPerTickResource(45),
                                      dtcm=DTCMResource(100),
                                      sdram=SDRAMResource(sdram_requirements))

        # sort out machine time step
        if machine_time_step is None:
            self._machine_time_step = config.get("Machine", "machineTimeStep")
            if self._machine_time_step == "None":
                raise exceptions.ConfigurationException(
                    "Needs a machine time step that is not None, add to the "
                    "initiation or to a .spiNNakerGraphFrontEnd.cfg")
            else:
                self._machine_time_step = int(self._machine_time_step)
        else:
            self._machine_time_step = machine_time_step

        # sort out time scale factor
        if time_scale_factor is None:
            self._time_scale_factor = config.get("Machine", "timeScaleFactor")
            if self._time_scale_factor == "None":
                raise exceptions.ConfigurationException(
                    "Needs a time scale factor that is not None, add to the "
                    "initiation or to a .spiNNakerGraphFrontEnd.cfg")
            else:
                self._time_scale_factor = int(self._time_scale_factor)
        else:
            self._time_scale_factor = time_scale_factor

        PartitionedVertex.__init__(
            self, label=label, resources_required=resources,
            constraints=constraints)
        AbstractPartitionedDataSpecableVertex.__init__(
            self, machine_time_step=self._machine_time_step,
            timescale_factor=self._time_scale_factor)
        AbstractProvidesOutgoingPartitionConstraints.__init__(self)

        if port is not None:
            self.add_constraint(
                TagAllocatorRequireReverseIptagConstraint(
                    port, sdp_port, board_address, tag))

        x, y, p = placement
        self.add_constraint(PlacerChipAndCoreConstraint(x, y, p))
        self._sdp_port = sdp_port

        if isinstance(mode, Enum):
            self._mode = mode.value
        else:
            self._mode = mode

    def get_binary_file_name(self):
        """
        binary name
        :return:
        """
        if self._mode == MODES.KEY_VALUE.value:
            return "key_value_root.aplx"
        elif self._mode == MODES.RELATIONAL.value:
            return "relational_root.aplx"
        elif self._mode == MODES.BOTH.value:
            return "both_root.aplx"
        else:
            raise exceptions.ConfigurationException(
                "DO not recongise the mode. So dont know which binary to use")

    def model_name(self):
        """
        human readable name
        :return:
        """
        if self._mode == MODES.KEY_VALUE.value:
            return "key_value_root"
        elif self._mode == MODES.RELATIONAL.value:
            return "relational_root"
        elif self._mode == MODES.BOTH.value:
            return "both_root"
        else:
            raise exceptions.ConfigurationException(
                "DO not recongise the mode. So dont know which name to use")

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
        :param ip_tags: the collection of iptags generated by the tag allocator
        :param reverse_ip_tags: the collection of reverse iptags generated by
        the tag allocator
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

        # Setup words + 1 for flags + 1 for recording size
        setup_size = constants.DATA_SPECABLE_BASIC_SETUP_INFO_N_WORDS * 4

        # Reserve SDRAM space for memory areas:
        self._reserve_memory_regions(spec, setup_size)

        # write basic setup data
        self._write_basic_setup_info(spec, self.DATA_REGIONS.SYSTEM.value)

        # write sdp port
        self._write_sdp_port(spec)

        # write multicast key
        self._write_multi_cast_key(spec, routing_info, sub_graph,
                                   self.DATA_REGIONS.TRANSMISSIONS.value)

        # write string size
        self._write_database_size(spec)

        # End-of-Spec:
        spec.end_specification()

        # close writer
        data_writer.close()

        # return file path for writer
        return data_writer.filename

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
        spec.reserve_memory_region(region=self.DATA_REGIONS.SYSTEM.value,
                                   size=system_size, label='systemInfo')
        spec.reserve_memory_region(region=self.DATA_REGIONS.SDP_PORT.value,
                                   size=self.SDP_REGION_SIZE, label="SDP_PORT")
        spec.reserve_memory_region(region=self.DATA_REGIONS.TRANSMISSIONS.value,
                                   size=self.TRANSMISSION_SIZE, label="MC_KEY")
        spec.reserve_memory_region(region=self.DATA_REGIONS.STRING_DATA.value,
                                   size=self.STRING_DATA_SIZE, label="inputs")

    def _write_sdp_port(self, spec):
        """
        writes the sdp port number for c configuration
        :param spec: the spec to write
        :return: None
        """
        spec.switch_write_focus(self.DATA_REGIONS.SDP_PORT.value)
        spec.write_value(self._sdp_port)

    def _write_database_size(self, spec):
        """
        adds the size of the database region into the region for c configuration
        :param spec: the dsg writer
        :return:
        """
        spec.switch_write_focus(region=self.DATA_REGIONS.STRING_DATA.value)
        spec.write_value(data=self.STRING_DATA_SIZE)

    def _write_multi_cast_key(self, spec, routing_info, subgraph, region_id):
        """
        writes the multicast key used during transmissions
        :param spec: dsg writer
        :param routing_info: key info object
        :param subgraph: partitioned graph
        :param region_id: the region to put this data
        :return: None
        """

        # Every subedge should have the same key
        partitions = subgraph.outgoing_edges_partitions_from_vertex(self)
        keys = partitions.keys()
        key = None
        if len(keys) > 0:
            keys_and_masks = \
                routing_info.get_keys_and_masks_from_partition(partitions[keys[0]])
            key = keys_and_masks[0].key

        spec.switch_write_focus(region=region_id)

        # Write Key info for this core:
        if key is None:
            spec.write_value(data=0)
            spec.write_value(data=0)
        else:
            spec.write_value(data=1)
            spec.write_value(data=key)

    def is_partitioned_data_specable(self):
        """
        helper method for isinstance
        :return:
        """
        return True
