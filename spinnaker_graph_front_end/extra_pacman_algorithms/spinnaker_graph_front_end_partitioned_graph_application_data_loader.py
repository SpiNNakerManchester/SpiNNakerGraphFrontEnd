"""
SpinnakerGraphFrontEndApplicationDataLoader
"""

# pacman imports
from pacman.utilities.utility_objs.progress_bar import ProgressBar

# spinn front end common imports
from spinn_front_end_common.abstract_models.\
    abstract_data_specable_vertex import \
    AbstractDataSpecableVertex

# graph front end imports
from spinnaker_graph_front_end.\
    abstract_partitioned_data_specable_vertex import \
    AbstractPartitionedDataSpecableVertex

# spinnman imports
from spinnman.data.file_data_reader import FileDataReader \
    as SpinnmanFileDataReader

import logging

logger = logging.getLogger(__name__)


class SpinnakerGraphFrontEndPartitionedGraphApplicationDataLoader(object):
    """
    SpinnakerGraphFrontEndPartitionedGraphApplicationDataLoader
    """

    def __call__(self, placements, txrx, processor_to_app_data_base_address,
                 vertex_to_app_data_files):
        # go through the placements and see if there's any application data to
        # load
        progress_bar = ProgressBar(len(list(placements.placements)),
                                   "Loading application data onto the machine")
        for placement in placements.placements:
            associated_vertex = placement.subvertex

            if (isinstance(associated_vertex, AbstractDataSpecableVertex) or
                isinstance(associated_vertex,
                           AbstractPartitionedDataSpecableVertex)):
                logger.debug("loading application data for vertex {}"
                             .format(associated_vertex.label))
                key = (placement.x, placement.y, placement.p)
                start_address = \
                    processor_to_app_data_base_address[key]['start_address']
                memory_written = \
                    processor_to_app_data_base_address[key]['memory_written']

                application_file_paths = \
                    vertex_to_app_data_files[placement.subvertex]
                for file_path_for_application_data in application_file_paths:
                    application_data_file_reader = SpinnmanFileDataReader(
                        file_path_for_application_data)
                    logger.debug("writing application data for vertex {}"
                                 .format(associated_vertex.label))
                    txrx.write_memory(
                        placement.x, placement.y, start_address,
                        application_data_file_reader, memory_written)

                    # update user 0 so that it points to the start of the
                    # applications data region on sdram
                    logger.debug("writing user 0 address for vertex {}"
                                 .format(associated_vertex.label))
                    user_o_register_address = \
                        txrx.get_user_0_register_address_from_core(
                            placement.x, placement.y, placement.p)
                    txrx.write_memory(placement.x, placement.y,
                                      user_o_register_address, start_address)
            progress_bar.update()
        progress_bar.end()

        return {"LoadedApplicationDataToken": True}
