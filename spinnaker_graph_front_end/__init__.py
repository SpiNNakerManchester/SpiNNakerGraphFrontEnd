# graph front end imports
from spinnaker_graph_front_end._version import \
    __version__, __version_name__, __version_month__, __version_year__
from spinnaker_graph_front_end.spinnaker import SpiNNaker
from spinnaker_graph_front_end import spinnaker

# front end common imports
from spinn_utilities.socket_address import SocketAddress
from spinn_front_end_common.utilities.utility_objs.executable_finder \
    import ExecutableFinder
from spinn_front_end_common.utilities import globals_variables

# utility models for graph front ends
from spinn_front_end_common.utility_models.live_packet_gather \
    import LivePacketGather
from spinn_front_end_common.utility_models.reverse_ip_tag_multi_cast_source \
    import ReverseIpTagMultiCastSource
from pacman.model.graphs.machine import MachineEdge

import os
import logging
import sys

logger = logging.getLogger(__name__)

_none_labelled_vertex_count = None
_none_labelled_edge_count = None

__all__ = ['LivePacketGather', 'ReverseIpTagMultiCastSource', 'MachineEdge',
           'setup', 'run', 'stop', 'read_xml_file', 'add_vertex_instance',
           'add_vertex', 'add_machine_vertex', 'add_machine_vertex_instance',
           'add_edge', 'add_application_edge_instance', 'add_machine_edge',
           'add_machine_edge_instance', 'add_socket_address', 'get_txrx',
           'get_machine_dimensions', 'get_number_of_cores_on_machine',
           'has_ran', 'machine_time_step', 'no_machine_time_steps',
           'timescale_factor', 'machine_graph', 'application_graph',
           'routing_infos', 'placements', 'transceiver', 'graph_mapper',
           'buffer_manager', 'machine', 'is_allocated_machine']


def setup(hostname=None, graph_label=None, model_binary_module=None,
          model_binary_folder=None, database_socket_addresses=None,
          user_dsg_algorithm=None, n_chips_required=None,
          extra_pre_run_algorithms=None, extra_post_run_algorithms=None,
          time_scale_factor=None, machine_time_step=None):
    """

    :param hostname:\
        the hostname of the SpiNNaker machine to operate on\
        (over rides the machine_name from the cfg file).
    :type hostname: str
    :param graph_label:\
        a human readable label for the graph (used mainly in reports)
    :type graph_label: str
    :param model_binary_module:\
        the module where the binary files can be found for the c code that is \
        being used in this application; mutually exclusive with the \
        model_binary_folder.
    :type model_binary_module: python module
    :param model_binary_folder:\
        the folder where the binary files can be found for the c code that is\
        being used in this application; mutually exclusive with the\
        model_binary_module.
    :type model_binary_folder: str
    :param database_socket_addresses:\
        set of SocketAddresses that need to be added for the database\
        notification functionality. This are over and above the ones used by\
        the LiveEventConnection
    :type database_socket_addresses: list of SocketAddresses
    :param user_dsg_algorithm:\
        an algorithm used for generating the application data which is loaded\
        onto the machine. if not set, will use the data specification language\
        algorithm required for the type of graph being used.
    :type user_dsg_algorithm: str
    :param n_chips_required:\
        if you need to be allocated a machine (for spalloc) before building\
        your graph, then fill this in with a general idea of the number of\
        chips you need so that the spalloc system can allocate you a machine\
        big enough for your needs.
    :type n_chips_required: int
    :param extra_pre_run_algorithms:\
        algorithms which need to be ran after mapping and loading has occurred\
        but before the system has ran. These are plugged directly into the\
        work flow management.
    :type extra_post_run_algorithms: list of str
    :param extra_post_run_algorithms:\
        algorithms which need to be ran after the simulation has ran. These\
        could be post processing of generated data on the machine for example.
    :type extra_pre_run_algorithms: list of str
    """
    global _none_labelled_vertex_count
    global _none_labelled_edge_count

    logger.info(
        "SpiNNaker graph front end (c) {}, "
        "University of Manchester".format(__version_year__))
    parent_dir = os.path.split(os.path.split(spinnaker.__file__)[0])[0]
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
    else:
        file_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        executable_finder.add_path(file_dir)

    # set up the spinnaker object
    SpiNNaker(
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
    globals_variables.get_simulator().run(duration)


def run_until_complete():
    """ Run until the application is complete
    """
    globals_variables.get_simulator().run_until_complete()


def stop():
    """ Do any necessary cleaning up before exiting. Unregisters the controller
    """
    global _executable_finder

    globals_variables.get_simulator().stop()
    _executable_finder = None


def read_xml_file(file_path):
    """ Reads a xml file and translates it into an application graph and \
        machine graph (if required)

    :param file_path: the file path in absolute form
    :rtype: None
    """
    logger.warn("This functionality is not yet supported")
    globals_variables.get_simulator().read_xml_file(file_path)


def add_vertex(cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass: the class object for creating the vertex
    :param cellparams: the input params for the class object
    :param constraints: any constraints to be applied to the vertex once built
    :param label: the label for this vertex
    :type cellclass: python object
    :type cellparams: dictionary of name and value
    :type constraints: list of AbstractConstraint
    :type label: str
    :return: the vertex instance object
    """
    spinnaker = globals_variables.get_simulator()

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(spinnaker.none_labelled_vertex_count)
        spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(spinnaker.none_labelled_vertex_count)
        spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add vertex
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    spinnaker.add_application_vertex(vertex)
    return vertex


def add_vertex_instance(vertex_to_add):
    """
    :param vertex_to_add: vertex instance to add to the graph
    :type vertex_to_add: instance of AbstractPartitionabelVertex
    :rtype: None
    """
    globals_variables.get_simulator().add_application_vertex(vertex_to_add)


def add_machine_vertex(
        cellclass, cellparams, label=None, constraints=None):
    """

    :param cellclass: the class object for creating the vertex
    :param cellparams: the input params for the class object
    :param constraints: any constraints to be applied to the vertex once built
    :param label: the label for this vertex
    :type cellclass: python object
    :type cellparams: dictionary of name and value
    :type constraints: list of AbstractConstraint
    :type label: str
    :return: the vertex instance object
    """
    spinnaker = globals_variables.get_simulator()

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Vertex {}".format(spinnaker.none_labelled_vertex_count)
        spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Vertex {}".format(spinnaker.none_labelled_vertex_count)
        spinnaker.increment_none_labelled_vertex_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add vertex
    cellparams['constraints'] = constraints
    vertex = cellclass(**cellparams)
    spinnaker.add_machine_vertex(vertex)
    return vertex


def add_machine_vertex_instance(vertex_to_add):
    """

    :param vertex_to_add: the vertex to add to the partitioned graph
    :rtype: None
    """
    globals_variables.get_simulator().add_machine_vertex(vertex_to_add)


def add_edge(cell_type, cellparams, semantic_label, label=None):
    spinnaker = globals_variables.get_simulator()

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Edge {}".format(spinnaker.none_labelled_edge_count)
        spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Edge {}".format(spinnaker.none_labelled_edge_count)
        spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add edge
    edge = cell_type(**cellparams)
    spinnaker.add_application_edge(edge, semantic_label)
    return edge


def add_application_edge_instance(edge, partition_id):
    globals_variables.get_simulator().add_application_edge(edge, partition_id)


def add_machine_edge_instance(edge, partition_id):
    globals_variables.get_simulator().add_machine_edge(edge, partition_id)


def add_machine_edge(cellclass, cellparams, semantic_label, label=None):
    spinnaker = globals_variables.get_simulator()

    # correct label if needed
    if label is None and 'label' not in cellparams:
        label = "Edge {}".format(spinnaker.none_labelled_edge_count)
        spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif 'label' in cellparams and cellparams['label'] is None:
        label = "Edge {}".format(spinnaker.none_labelled_edge_count)
        spinnaker.increment_none_labelled_edge_count()
        cellparams['label'] = label
    elif label is not None:
        cellparams['label'] = label

    # add edge
    edge = cellclass(**cellparams)
    spinnaker.add_machine_edge(edge, semantic_label)
    return edge


def add_socket_address(
        database_ack_port_num, database_notify_host, database_notify_port_num):
    """
    adds a socket address for the notification protocol

    :param database_ack_port_num: port num to send acknowledgement to
    :param database_notify_host: host ip to send notification to
    :param database_notify_port_num: port that the external device will be\
        notified on.
    """
    database_socket = SocketAddress(
        listen_port=database_ack_port_num,
        notify_host_name=database_notify_host,
        notify_port_no=database_notify_port_num)

    globals_variables.get_simulator().add_socket_address(database_socket)


def get_txrx():
    """
    returns the transceiver used by the tool chain
    """
    return globals_variables.get_simulator().transceiver


def get_machine_dimensions():
    """
    returns the x and y dimension of the machine
    """
    return globals_variables.get_simulator().get_machine_dimensions()


def get_number_of_cores_on_machine():
    """
    returns the number of cores on this machine
    """
    this_machine = globals_variables.get_simulator().machine
    cores, _ = this_machine.get_cores_and_link_count()
    return cores


def has_ran():
    return globals_variables.get_simulator().has_ran


def machine_time_step():
    return globals_variables.get_simulator().machine_time_step


def no_machine_time_steps():
    return globals_variables.get_simulator().no_machine_time_steps


def timescale_factor():
    return globals_variables.get_simulator().time_scale_factor


def machine_graph():
    return globals_variables.get_simulator().machine_graph


def application_graph():
    return globals_variables.get_simulator().application_graph


def routing_infos():
    return globals_variables.get_simulator().routing_infos


def placements():
    return globals_variables.get_simulator().placements


def transceiver():
    return globals_variables.get_simulator().transceiver


def graph_mapper():
    return globals_variables.get_simulator().graph_mapper


def buffer_manager():
    """
    :return: the buffer manager being used for loading/extracting buffers

    """
    return globals_variables.get_simulator().buffer_manager


def machine():
    return globals_variables.get_simulator().machine


def is_allocated_machine():
    return globals_variables.get_simulator().is_allocated_machine
