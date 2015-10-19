from pacman.utilities.utility_objs.progress_bar import ProgressBar
from spinn_front_end_common.abstract_models.abstract_data_specable_vertex import \
    AbstractDataSpecableVertex
from spinn_front_end_common.utilities.executable_targets import \
    ExecutableTargets
from spinn_front_end_common.utilities import exceptions
from spynnaker_graph_front_end.abstract_partitioned_data_specable_vertex import \
    AbstractPartitionedDataSpecableVertex


class SpinnakerGraphFrontEndDataSpecificationWriter(object):
    """
    SpinnakerGraphFrontEndDataSpecificationWriter
    """

    def __call__(
            self, placements, partitionable_graph, graph_mapper, tags,
            partitioned_graph, routing_infos, hostname,
            report_default_directory, write_text_specs,
            app_data_runtime_folder, executable_finder):

        """ generates the dsg for the graph.

        :return:
        """

        # iterate though subvertexes and call generate_data_spec for each
        # vertex
        executable_targets = ExecutableTargets()
        dsg_targets = dict()

        # create a progress bar for end users
        progress_bar = ProgressBar(len(list(placements.placements)),
                                   "Generating data specifications")
        for placement in placements.placements:
            binary_name = None
            if len(partitionable_graph.vertices) > 0:
                associated_vertex =\
                    graph_mapper.get_vertex_from_subvertex(placement.subvertex)

                # if the vertex can generate a DSG, call it
                if isinstance(associated_vertex, AbstractDataSpecableVertex):
                    ip_tags = tags.get_ip_tags_for_vertex(
                        placement.subvertex)
                    reverse_ip_tags = tags.get_reverse_ip_tags_for_vertex(
                        placement.subvertex)
                    file_paths = associated_vertex.generate_data_spec(
                        placement.subvertex, placement,
                        partitioned_graph, partitionable_graph,
                        routing_infos, hostname,
                        graph_mapper, report_default_directory,
                        ip_tags, reverse_ip_tags, write_text_specs,
                        app_data_runtime_folder)
                    progress_bar.update()

                    # link dsg file to subvertex
                    dsg_targets[placement.subvertex] = list()
                    for file_path in file_paths:
                        dsg_targets[placement.subvertex].append(file_path)

                    # Get name of binary from vertex
                    binary_name = associated_vertex.get_binary_file_name()

                    # Attempt to find this within search paths
                    binary_path = executable_finder.get_executable_path(
                        binary_name)
                    if binary_path is None:
                        raise exceptions.ExecutableNotFoundException(
                            binary_name)

                    if not executable_targets.has_binary(binary_path):
                        executable_targets.add_binary(binary_path)
                    executable_targets.add_processor(
                        binary_path, placement.x, placement.y, placement.p)
            else:
                if isinstance(placement.subvertex,
                              AbstractPartitionedDataSpecableVertex):
                    ip_tags = tags.get_ip_tags_for_vertex(
                        placement.subvertex)
                    reverse_ip_tags = \
                        tags.get_reverse_ip_tags_for_vertex(
                            placement.subvertex)
                    file_paths = placement.subvertex.generate_data_spec(
                        placement, partitioned_graph,
                        routing_infos, hostname,
                        report_default_directory, ip_tags,
                        reverse_ip_tags, write_text_specs,
                        app_data_runtime_folder)

                    # link dsg file to subvertex
                    dsg_targets[placement.subvertex] = list()
                    for file_path in file_paths:
                        dsg_targets[placement.subvertex].append(file_path)

                    progress_bar.update()

                    # Get name of binary from vertex
                    binary_name = placement.subvertex.get_binary_file_name()

                    # Attempt to find this within search paths
                    binary_path = executable_finder.get_executable_path(
                        binary_name)
                    if binary_path is None:
                        raise exceptions.ExecutableNotFoundException(
                            binary_name)

                    if not executable_targets.has_binary(binary_path):
                        executable_targets.add_binary(binary_path)
                    executable_targets.add_processor(
                        binary_path, placement.x, placement.y, placement.p)
                else:
                    progress_bar.update()

                    # Get name of binary from vertex
                    binary_name = placement.subvertex.get_binary_file_name()

                    # Attempt to find this within search paths
                    binary_path = executable_finder.get_executable_path(
                        binary_name)
                    if binary_path is None:
                        raise exceptions.ExecutableNotFoundException(
                            binary_name)

                    if not executable_targets.has_binary(binary_path):
                        executable_targets.add_binary(binary_path)
                    executable_targets.add_processor(
                        binary_path, placement.x, placement.y, placement.p)

        # finish the progress bar
        progress_bar.end()

        return {'executable_targets': executable_targets,
                'dsg_targets': dsg_targets}
