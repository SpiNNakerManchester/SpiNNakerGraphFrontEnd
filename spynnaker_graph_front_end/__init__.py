from spinn_front_end_common.interface.executable_finder import ExecutableFinder

# utility models for graph front ends
from spinn_front_end_common.utility_models.\
    reverse_ip_tag_multi_cast_source import ReverseIpTagMultiCastSource
from spinn_front_end_common.utility_models.command_sender import CommandSender
from spinn_front_end_common.utility_models.live_packet_gather \
    import LivePacketGather
from pacman.model.partitioned_graph.multi_cast_partitioned_edge \
    import MultiCastPartitionedEdge
from pacman.model.partitionable_graph.multi_cast_partitionable_edge \
    import MultiCastPartitionableEdge

_spinnaker = None
_none_labelled_vertex_count = None
_none_labelled_edge_count = None

def setup(hostname=None, graph_label=None, model_binary_folder=None):
    """ for builders with pynn attitude, allows end users to define wherever
    their binaries are

    :param hostname:
    :param graph_label:
    :param model_binary_folder:
    :return:
    """
    from spynnaker_graph_front_end.spinnaker_graph_front_end import \
        SpiNNakerGraphFrontEnd
    import os
    global _spinnaker
    global _none_labelled_vertex_count
    global _none_labelled_edge_count

    executable_finder = ExecutableFinder()
    executable_finder.add_path(os.path.dirname(model_binary_folder.__file__))
    # set up the spinnaker object
    _spinnaker = SpiNNakerGraphFrontEnd(hostname, graph_label,
                                        executable_finder)
    # set up none label count params.
    _none_labelled_edge_count = 0
    _none_labelled_vertex_count = 0


def run(duration=None):
    """
    method to support running an application for a number of microseconds
    :param duration: the number of microseconds the application should run for
    :type duration: int
    """
    import sys
    global _spinnaker

    if duration is None:
        duration = sys.maxint
    _spinnaker.run(duration)


def stop(stop_on_board=True):
    """
    Do any necessary cleaning up before exiting.

    Unregisters the controller
    :param stop_on_board: decides if the routing tbales and tag should be
    removed from the machine at stop
    """
    global _spinnaker
    global _executable_finder

    _spinnaker.stop(stop_on_board)
    _spinnaker = None
    _executable_finder = None


def read_xml_file(file_path):
    """
    helper method for people who use this as an import.
    reads a xml file and translates it into a graph and partitioned graph
    (if required)
    :param file_path: the file path in absulete form
    :return: None
    """
    global _spinnaker
    _spinnaker.read_xml_file(file_path)


def add_vertex(cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass:
    :param cellparams:
    :param constraints:
    :param label:
    :return:
    """
    global _spinnaker
    global _none_labelled_vertex_count

    # corect label if needed
    if label is None:
        label = "Vertex {}".format(_none_labelled_vertex_count)
        _none_labelled_vertex_count += 1
    # add vertex
    cellparams['label'] = label
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    _spinnaker.add_partitionable_vertex(vertex)
    return vertex


def add_edge(cell_type, cellparams, label=None, constraints=None):
    """

    :param cell_type:
    :param cellparams:
    :param constraints:
    :param label:
    :return:
    """
    global _spinnaker
    global _none_labelled_edge_count

    if label is None:
        label = "Edge {}".format(_none_labelled_edge_count)
        _none_labelled_edge_count += 1
    cellparams['label'] = label
    cellparams['constraints'] = constraints
    edge = cell_type(**cellparams)
    _spinnaker.add_partitionable_edge(edge)
    return edge


def add_partitioned_vertex(cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass:
    :param cellparams:
    :param label:
    :param constraints:
    :return:
    """
    global _spinnaker
    global _none_labelled_vertex_count
    # corect label if needed
    if label is None:
        label = "Vertex {}".format(_none_labelled_vertex_count)
        _none_labelled_vertex_count += 1
    # add vertex
    cellparams['label'] = label
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    _spinnaker.add_partitioned_vertex(vertex)
    return vertex


def add_partitioned_edge(cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass:
    :param cellparams:
    :param constraints:
    :param label:
    :return:
    """
    global _spinnaker
    global _none_labelled_edge_count

    if label is None:
        label = "Edge {}".format(_none_labelled_edge_count)
        _none_labelled_edge_count += 1
    cellparams['label'] = label
    cellparams['constraints'] = constraints
    edge = cellclass(**cellparams)
    _spinnaker.add_partitioned_edge(edge)
    return edge


def get_machine_dimensions():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.get_machine_dimensions()