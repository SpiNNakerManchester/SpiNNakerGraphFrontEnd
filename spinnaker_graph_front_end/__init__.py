from spinn_front_end_common.interface.executable_finder import ExecutableFinder

from spinnaker_graph_front_end.utilities import conf
from spinnaker_graph_front_end._version import \
    __version__, __version_name__, __version_month__, __version_year__
# utility models for graph front ends

import logging

logger = logging.getLogger(__name__)


_spinnaker = None
_none_labelled_vertex_count = None
_none_labelled_edge_count = None


def setup(hostname=None, graph_label=None, model_binary_module=None,
          model_binary_folder=None, database_socket_addresses=None,
          algorithms_for_auto_pause_and_resume=None):
    """ for builders with pynn attitude, allows end users to define wherever\
        their binaries are

    :param hostname:
    :param graph_label:
    :param model_binary_module:
    :param model_binary_folder:
    :param database_socket_addresses:
    :param algorithms_for_auto_pause_and_resume:

    :return:
    """
    from spinnaker_graph_front_end.spinnaker import SpiNNaker
    from spinnaker_graph_front_end import spinnaker
    import os
    global _spinnaker
    global _none_labelled_vertex_count
    global _none_labelled_edge_count

    logger.info(
        "SpiNNaker graph front end (c) {} APT Group, University of Manchester"
        .format(__version_year__))
    parent_dir = os.path.split(os.path.split(
        spinnaker.__file__)[0])[0]
    logger.info(
        "Release version {}({}) - {} {}. Installed in folder {}".format(
            __version__, __version_name__, __version_month__, __version_year__,
            parent_dir))

    # add the directorities for where to locate the binaries
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
        extra_algorithms_for_auto_pause_and_resume=
        algorithms_for_auto_pause_and_resume)


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
    cellparams['constraints'] = constraints
    edge = cell_type(**cellparams)
    _spinnaker.add_partitionable_edge(edge, partition_id)
    return edge


def add_partitionable_edge_instance(edge, partition_id):
    """

    :param edge:
    :param partition_id:
    :return:
    """
    _spinnaker.add_partitionable_edge(edge, partition_id)


def add_partitioned_edge_instance(edge, partition_id):
    """

    :param edge:
    :param partition_id:
    :return:
    """
    _spinnaker.add_partitioned_edge(edge, partition_id)


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
    global _none_labelled_vertex_count

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(_none_labelled_vertex_count)
        _none_labelled_vertex_count += 1
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(_none_labelled_vertex_count)
        _none_labelled_vertex_count += 1
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add partitioned vertex
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    _spinnaker.add_partitioned_vertex(vertex)
    return vertex


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
    global _none_labelled_edge_count

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(_none_labelled_edge_count)
        _none_labelled_edge_count += 1
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(_none_labelled_edge_count)
        _none_labelled_edge_count += 1
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add partitioned edge
    cellparams['constraints'] = constraints
    edge = cellclass(**cellparams)
    _spinnaker.add_partitioned_edge(edge, partition_id)
    return edge


def get_txrx():
    global _spinnaker
    return _spinnaker.transceiver


def get_machine_dimensions():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.get_machine_dimensions()
