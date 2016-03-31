# front end common imports
from spinn_front_end_common.utilities.utility_objs.executable_finder \
    import ExecutableFinder

# graph front end imports
from spinnaker_graph_front_end.utilities import conf
from spinnaker_graph_front_end._version import \
    __version__, __version_name__, __version_month__, __version_year__

# utility models for graph front ends
from spinn_front_end_common.utility_models.live_packet_gather \
    import LivePacketGather  # @IgnorePep8
from spinn_front_end_common.utility_models.reverse_ip_tag_multi_cast_source \
    import ReverseIpTagMultiCastSource  # @IgnorePep8
from pacman.model.partitioned_graph.multi_cast_partitioned_edge \
    import MultiCastPartitionedEdge


import logging
logger = logging.getLogger(__name__)


_spinnaker = None
_none_labelled_vertex_count = None
_none_labelled_edge_count = None


def setup(hostname=None, graph_label=None, model_binary_module=None,
          model_binary_folder=None, database_socket_addresses=None,
          user_dsg_algorithm=None):
    """

    :param hostname:
    :param graph_label:
    :param model_binary_module:
    :param model_binary_folder:
    :param database_socket_addresses:
    :param user_dsg_algorithm:

    :return:
    """
    from spinnaker_graph_front_end.spinnaker import SpiNNaker
    from spinnaker_graph_front_end import spinnaker
    import os
    global _spinnaker
    global _none_labelled_vertex_count
    global _none_labelled_edge_count

    logger.info(
        "SpiNNaker graph front end (c) {}, Alan Stokes, "
        "University of Manchester".format(__version_year__))
    parent_dir = os.path.split(os.path.split(
        spinnaker.__file__)[0])[0]
    logger.info(
        "Release version {}({}) - {} {}. Installed in folder {}".format(
            __version__, __version_name__, __version_month__, __version_year__,
            parent_dir))

    # add the directories where the binaries are located
    executable_finder = ExecutableFinder()
    if model_binary_module is not None:
        executable_finder.add_path(
            os.path.dirname(model_binary_module.__file__))
    elif model_binary_folder is not None:
        executable_finder.add_path(model_binary_folder)

    # set up the spinnaker object
    _spinnaker = SpiNNaker(
        host_name=hostname, graph_label=graph_label,
        executable_finder=executable_finder,
        database_socket_addresses=database_socket_addresses,
        dsg_algorithm=user_dsg_algorithm)


def run(duration=None):
    """ Method to support running an application for a number of microseconds

    :param duration: the number of microseconds the application should run for
    :type duration: int
    """
    import sys
    global _spinnaker

    if duration is None:
        duration = sys.maxint
    _spinnaker.run(duration)


def stop():
    """ Do any necessary cleaning up before exiting. Unregisters the controller
    """
    global _spinnaker
    global _executable_finder

    _spinnaker.stop()
    _spinnaker = None
    _executable_finder = None


def read_xml_file(file_path):
    """ Reads a xml file and translates it into a graph and partitioned graph\
        (if required)

    :param file_path: the file path in absolute form
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

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(_spinnaker.none_labelled_vertex_count)
        _spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(_spinnaker.none_labelled_vertex_count)
        _spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add vertex
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    _spinnaker.add_partitionable_vertex(vertex)
    return vertex


def add_vertex_instance(vertex_to_add):
    """

    :param vertex_to_add:
    :return:
    """
    global _spinnaker
    _spinnaker.add_partitionable_vertex(vertex_to_add)


def add_partitioned_vertex(
        cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass:
    :param cellparams:
    :param label:
    :param constraints:
    :return:
    """
    global _spinnaker

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(_spinnaker.none_labelled_vertex_count)
        _spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(_spinnaker.none_labelled_vertex_count)
        _spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add partitioned vertex
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    _spinnaker.add_partitioned_vertex(vertex)
    return vertex


def add_partitioned_vertex_instance(vertex_to_add):
    """

    :param vertex_to_add:
    :return:
    """
    global _spinnaker
    _spinnaker.add_partitioned_vertex(vertex_to_add)


def add_edge(cell_type, cellparams, label=None, constraints=None,
             partition_id=None):
    """

    :param cell_type:
    :param cellparams:
    :param constraints:
    :param label:
    :param partition_id:
    :return:
    """
    global _spinnaker

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add edge
    edge = cell_type(**cellparams)
    _spinnaker.add_partitionable_edge(edge, partition_id, constraints)
    return edge


def add_partitionable_edge_instance(edge, partition_id, constraints):
    """

    :param edge:
    :param partition_id:
    :param constraints:
    :return:
    """
    _spinnaker.add_partitionable_edge(edge, partition_id, constraints)


def add_partitioned_edge_instance(edge, partition_id, constraints):
    """

    :param edge:
    :param partition_id:
    :param constraints:
    :return:
    """
    _spinnaker.add_partitioned_edge(edge, partition_id, constraints)


def add_partitioned_edge(cellclass, cellparams, label=None, constraints=None,
                         partition_id=None):
    """

    :param cellclass:
    :param cellparams:
    :param constraints:
    :param label:
    :param partition_id:
    :return:
    """
    global _spinnaker

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add partitioned edge
    edge = cellclass(**cellparams)
    _spinnaker.add_partitioned_edge(edge, partition_id, constraints)
    return edge


def get_txrx():
    """
    returns the transceiver used by the tool chain
    :return:
    """
    global _spinnaker
    return _spinnaker.transceiver


def get_machine_dimensions():
    """
    returns the x and y dimension of the machine
    :return:
    """
    global _spinnaker
    return _spinnaker.get_machine_dimensions()


def get_number_of_cores_on_machine():
    """
    returns the number of cores on this machine
    :return:
    """
    global _spinnaker
    this_machine = _spinnaker.machine
    cores, _ = this_machine.get_cores_and_link_count()
    return cores


def has_ran():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.has_ran


def machine_time_step():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.machine_time_step


def no_machine_time_steps():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.no_machine_time_steps


def timescale_factor():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.time_scale_factor


def partitioned_graph():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.partitioned_graph


def partitionable_graph():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.partitionable_graph


def routing_infos():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.routing_infos


def placements():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.placements


def transceiver():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.txrx


def graph_mapper():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.graph_mapper


def buffer_manager():
    """
    returns the buffer manager being used for loading/extracting buffers
    :return:
    """
    global _spinnaker
    return _spinnaker.buffer_manager


def machine():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.machine
