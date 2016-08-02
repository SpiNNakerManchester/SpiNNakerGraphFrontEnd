# front end common imports
from spinn_front_end_common.utilities.notification_protocol.socket_address \
    import SocketAddress
from spinn_front_end_common.utilities.utility_objs.executable_finder \
    import ExecutableFinder

# graph front end imports
from spinnaker_graph_front_end._version import \
    __version__, __version_name__, __version_month__, __version_year__
from spinnaker_graph_front_end.spinnaker import SpiNNaker

# utility models for graph front ends
from spinn_front_end_common.utility_models.live_packet_gather \
    import LivePacketGather  # @IgnorePep8
from spinn_front_end_common.utility_models.reverse_ip_tag_multi_cast_source \
    import ReverseIpTagMultiCastSource  # @IgnorePep8
from pacman.model.graphs.machine.impl.machine_edge \
    import MachineEdge  # @IgnorePep8


import logging
logger = logging.getLogger(__name__)


_spinnaker = None
_none_labelled_vertex_count = None
_none_labelled_edge_count = None


def setup(hostname=None, graph_label=None, model_binary_module=None,
          model_binary_folder=None, database_socket_addresses=None,
          user_dsg_algorithm=None, n_chips_required=None,
          extra_pre_run_algorithms=None, extra_post_run_algorithms=None,
          time_scale_factor=None, machine_time_step=None):
    """

    :param hostname: the hostname of the SpiNNaker machine to operate on
    (over rides the machine_name from the cfg file).
    :param graph_label: a human readable label for the graph (used mainly in
    reports)
    :param model_binary_module: the module where the binary files can be found
    for the c code that is being used in this application mutally exclusive with
    the model_binary_folder.
    :param model_binary_folder: the folder where the binary files can be found
    for the c code that is being used in this application mutally exclusive with
    the model_binary_module.
    :param database_socket_addresses: set of SocketAddresses that need to be
    added for the database functionality. This are over and above the ones used
    by the liveEventConnection
    :param user_dsg_algorithm: a algorithm used for generating the application
    data which is loaded onto the machine. if not set, will use the
    data specification language algorithm required for the type of graph being
    used.
    :param n_chips_required: if you need to be allocated a machine (for spalloc)
    before building your graph, then fill this in with a general idea of the
    number of chips you need so that the spalloc system can allocate you a
    machine big enough for your needs.
    :param extra_pre_run_algorithms: algorithms which need to be ran after
    mapping and loading has occured but before the system has ran. These are
    plugged directly into the work flow management.
    :param extra_post_run_algorithms: algorithms which need to be ran after the
    simulation has ran. These could be post processing of generated data on the
    machine for example.
    :type hostname: str
    :type graph_label: str
    :type model_binary_folder: str
    :type model_binary_module: python module
    :type database_socket_addresses: list of SocketAddresses
    :type user_dsg_algorithm: str
    :type n_chips_required: int
    :type extra_post_run_algorithms: list of str
    :type extra_pre_run_algorithms: list of str
    :return: None
    """
    from spinnaker_graph_front_end import spinnaker
    import os
    global _spinnaker
    global _none_labelled_vertex_count
    global _none_labelled_edge_count

    logger.info(
        "SpiNNaker graph front end (c) {}, "
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
        dsg_algorithm=user_dsg_algorithm,
        n_chips_required=n_chips_required,
        extra_pre_run_algorithms=extra_pre_run_algorithms,
        extra_post_run_algorithms=extra_post_run_algorithms,
        machine_time_step=machine_time_step,
        time_scale_factor=time_scale_factor)


def run(duration=None):
    """ Method to support running an application for a number of microseconds

    :param duration: the number of microseconds the application should run for
    :type duration: int
    """
    global _spinnaker

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
    """ Reads a xml file and translates it into an application graph and \
        machine graph (if required)

    :param file_path: the file path in absolute form
    :return: None
    """
    global _spinnaker
    logger.warn("This functionality is not yet supported")
    _spinnaker.read_xml_file(file_path)


def add_vertex(cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass: the class object for creating the vertex
    :param cellparams: the input params for the class object
    :param constraints: any constraints to be applied to the vertex once built
    :param label: the label for this vertex
    :type cellclass: python object
    :type cellparams: dictoanry of name and value
    :type constraints: list of AbstractConstraint
    :type label: str
    :return: the vertex instance object
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
    _spinnaker.add_application_vertex(vertex)
    return vertex


def add_vertex_instance(vertex_to_add):
    """
    :param vertex_to_add: vertex instance to add to the graph
    :type vertex_to_add: instance of AbstractPartitionabelVertex
    :return: None
    """
    global _spinnaker
    _spinnaker.add_application_vertex(vertex_to_add)


def add_machine_vertex(
        cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass: the class object for creating the vertex
    :param cellparams: the input params for the class object
    :param constraints: any constraints to be applied to the vertex once built
    :param label: the label for this vertex
    :type cellclass: python object
    :type cellparams: dictoanry of name and value
    :type constraints: list of AbstractConstraint
    :type label: str
    :return: the vertex instance object
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
    _spinnaker.add_machine_vertex(vertex)
    return vertex


def add_machine_vertex_instance(vertex_to_add):
    """

    :param vertex_to_add: the vertex to add to the partitioned graph
    :return: None
    """
    global _spinnaker
    _spinnaker.add_machine_vertex(vertex_to_add)


def add_edge(cell_type, cellparams, semantic_label, label=None):
    """

    :param cell_type:
    :param cellparams:
    :param semantic_label:
    :param constraints:
    :param label:
    :return:
    """
    global _spinnaker

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Edge {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Edge {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add edge
    edge = cell_type(**cellparams)
    _spinnaker.add_application_edge(edge, semantic_label)
    return edge


def add_application_edge_instance(edge, partition_id):
    """

    :param edge:
    :param partition_id:
    :return:
    """
    _spinnaker.add_application_edge(edge, partition_id)


def add_machine_edge_instance(edge, partition_id):
    """

    :param edge:
    :param partition_id:
    :return:
    """
    _spinnaker.add_machine_edge(edge, partition_id)


def add_machine_edge(cellclass, cellparams, semantic_label, label=None):
    """

    :param cellclass:
    :param cellparams:
    :param semantic_label:
    :param label:
    :return:
    """
    global _spinnaker

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Edge {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Edge {}".format(_spinnaker.none_labelled_edge_count)
        _spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add edge
    edge = cellclass(**cellparams)
    _spinnaker.add_machine_edge(edge, semantic_label)
    return edge


def add_socket_address(
        database_ack_port_num, database_notify_host, database_notify_port_num):
    """
    adds a socket address for the notification protocol
    :param database_ack_port_num: port num to send acknowledgement to
    :param database_notify_host: host ip to send notification to
    :param database_notify_port_num: port that the external device will be
    notified on.
    """
    global _spinnaker

    database_socket = SocketAddress(
        listen_port=database_ack_port_num,
        notify_host_name=database_notify_host,
        notify_port_no=database_notify_port_num)

    _spinnaker.add_socket_address(database_socket)


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


def machine_graph():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.machine_graph


def application_graph():
    """

    :return:
    """
    global _spinnaker
    return _spinnaker.application_graph


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
    return _spinnaker.transceiver


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


def is_allocated_machine():
    return SpiNNaker.is_allocated_machine
