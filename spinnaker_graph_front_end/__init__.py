# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
import sys
from spinn_utilities.socket_address import SocketAddress
from pacman.model.graphs.machine import MachineEdge
from spinn_front_end_common.utilities.utility_objs import ExecutableFinder
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.utility_models import (
    LivePacketGather, ReverseIpTagMultiCastSource)
from spinnaker_graph_front_end._version import (
    __version__, __version_name__, __version_month__, __version_year__)
from spinnaker_graph_front_end.spinnaker import SpiNNaker
from spinnaker_graph_front_end import spinnaker as gfe_file

logger = logging.getLogger(__name__)

_none_labelled_vertex_count = None
_none_labelled_edge_count = None

__all__ = ['LivePacketGather', 'ReverseIpTagMultiCastSource', 'MachineEdge',
           'setup', 'run', 'stop', 'read_xml_file', 'add_vertex_instance',
           'add_vertex', 'add_machine_vertex', 'add_machine_vertex_instance',
           'add_edge', 'add_application_edge_instance', 'add_machine_edge',
           'add_machine_edge_instance', 'add_socket_address', 'get_txrx',
           'has_ran', 'machine_time_step',
           'get_number_of_available_cores_on_machine', 'no_machine_time_steps',
           'time_scale_factor', 'machine_graph', 'application_graph',
           'routing_infos', 'placements', 'transceiver', 'graph_mapper',
           'buffer_manager', 'machine', 'is_allocated_machine']


def setup(hostname=None, graph_label=None, model_binary_module=None,
          model_binary_folder=None, database_socket_addresses=None,
          user_dsg_algorithm=None, n_chips_required=None,
          n_boards_required=None, extra_pre_run_algorithms=None,
          extra_post_run_algorithms=None,
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
        Deprecated! Use n_boards_required instead.
        Must be None if n_boards_required specified.
    :type n_chips_required: int or None
    :param n_boards_required:\
        if you need to be allocated a machine (for spalloc) before building\
        your graph, then fill this in with a general idea of the number of
        boards you need so that the spalloc system can allocate you a machine\
        big enough for your needs.
    :type n_boards_required: int or None
    :param extra_pre_run_algorithms:\
        algorithms which need to be ran after mapping and loading has occurred\
        but before the system has ran. These are plugged directly into the\
        work flow management.
    :type extra_post_run_algorithms: list of str
    :param extra_post_run_algorithms:\
        algorithms which need to be ran after the simulation has ran. These\
        could be post processing of generated data on the machine for example.
    :type extra_pre_run_algorithms: list of str
    :raises ConfigurationException if both n_chips_required and
        n_boards_required are used.
    """
    global _none_labelled_vertex_count
    global _none_labelled_edge_count

    logger.info(
        "SpiNNaker graph front end (c) {}, "
        "University of Manchester".format(__version_year__))
    parent_dir = os.path.split(os.path.split(gfe_file.__file__)[0])[0]
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
        n_boards_required=n_boards_required,
        extra_pre_run_algorithms=extra_pre_run_algorithms,
        extra_post_run_algorithms=extra_post_run_algorithms,
        machine_time_step=machine_time_step,
        time_scale_factor=time_scale_factor)


def _sim():
    """ Gets the current SpiNNaker simulator object.
    """
    return globals_variables.get_simulator()


def run(duration=None):
    """ Method to support running an application for a number of microseconds.

    :param duration: the number of microseconds the application should run for
    :type duration: int
    """
    _sim().run(duration)


def run_until_complete():
    """ Run until the application is complete
    """
    _sim().run_until_complete()


def stop():
    """ Do any necessary cleaning up before exiting. Unregisters the controller
    """
    global _executable_finder

    _sim().stop()
    _executable_finder = None


def stop_run():
    """ Stop a request to run forever
    """
    _sim().stop_run()


def read_xml_file(file_path):
    """ Reads a xml file and translates it into an application graph and \
        machine graph (if required).

    :param file_path: the file path in absolute form
    :rtype: None
    """
    logger.warning("This functionality is not yet supported")
    _sim().read_xml_file(file_path)


def add_vertex(cell_class, cell_params, label=None, constraints=None):
    """ Create an application vertex and add it to the unpartitioned graph.

    :param cell_class: the class object for creating the application vertex
    :param cell_params: the input parameters for the class object
    :param constraints: any constraints to be applied to the vertex once built
    :param label: the label for this vertex
    :type cell_class: class
    :type cell_params: dict(str,object)
    :type constraints: list(:py:class:`AbstractConstraint`) or None
    :type label: str or None
    :return: the application vertex instance object
    """
    if label is not None:
        cell_params['label'] = label
    # graph handles label is None
    cell_params['constraints'] = constraints
    # add vertex
    vertex = cell_class(**cell_params)
    add_vertex_instance(vertex)
    return vertex


def add_vertex_instance(vertex_to_add):
    """ Add an existing application vertex to the unpartitioned graph.

    :param vertex_to_add: vertex instance to add to the graph
    :type vertex_to_add: :py:class:`AbstractPartitionableVertex`
    :rtype: None
    """
    _sim().add_application_vertex(vertex_to_add)


def add_machine_vertex(
        cell_class, cell_params, label=None, constraints=None):
    """ Create a machine vertex and add it to the partitioned graph.

    :param cell_class: the class of the machine vertex to create
    :param cell_params: the input parameters for the class object
    :param constraints: any constraints to be applied to the vertex once built
    :param label: the label for this vertex
    :type cell_class: class
    :type cell_params: dict(str,object)
    :type constraints: list(:py:class:`AbstractConstraint`) or None
    :type label: str or None
    :return: the machine vertex instance object
    """
    if label is not None:
        cell_params['label'] = label
    # graph handles label is None
    cell_params['constraints'] = constraints
    # add vertex
    vertex = cell_class(**cell_params)
    add_machine_vertex_instance(vertex)
    return vertex


def add_machine_vertex_instance(vertex_to_add):
    """ Add an existing machine vertex to the partitioned graph.

    :param vertex_to_add: the vertex to add to the partitioned graph
    :rtype: None
    """
    _sim().add_machine_vertex(vertex_to_add)


def _new_edge_label():
    spinnaker = _sim()
    label = "Edge {}".format(spinnaker.none_labelled_edge_count)
    spinnaker.increment_none_labelled_edge_count()
    return label


def add_edge(edge_type, edge_parameters, semantic_label, label=None):
    """ Create an application edge and add it to the unpartitioned graph.

    :param edge_type: the kind (class) of application edge to create
    :param edge_parameters: dict of parameters to pass to the constructor
    :param semantic_label: the ID of the partition that the edge belongs to
    :param label: textual label for the edge, or None
    :return: the created application edge
    """
    # correct label if needed
    if label is None and 'label' not in edge_parameters:
        edge_parameters['label'] = _new_edge_label()
    elif 'label' in edge_parameters and edge_parameters['label'] is None:
        edge_parameters['label'] = _new_edge_label()
    elif label is not None:
        edge_parameters['label'] = label

    # add edge
    edge = edge_type(**edge_parameters)
    add_application_edge_instance(edge, semantic_label)
    return edge


def add_application_edge_instance(edge, partition_id):
    _sim().add_application_edge(edge, partition_id)


def add_machine_edge(edge_type, edge_parameters, semantic_label, label=None):
    """ Create a machine edge and add it to the partitioned graph.

    :param edge_type: the kind (class) of machine edge to create
    :param edge_parameters: dict of parameters to pass to the constructor
    :param semantic_label: the ID of the partition that the edge belongs to
    :param label: textual label for the edge, or None
    :return: the created machine edge
    """
    # correct label if needed
    if label is None and 'label' not in edge_parameters:
        edge_parameters['label'] = _new_edge_label()
    elif 'label' in edge_parameters and edge_parameters['label'] is None:
        edge_parameters['label'] = _new_edge_label()
    elif label is not None:
        edge_parameters['label'] = label

    # add edge
    edge = edge_type(**edge_parameters)
    add_machine_edge_instance(edge, semantic_label)
    return edge


def add_machine_edge_instance(edge, partition_id):
    _sim().add_machine_edge(edge, partition_id)


def add_socket_address(
        database_ack_port_num, database_notify_host, database_notify_port_num):
    """ Adds a socket address for the notification protocol.

    :param database_ack_port_num: port number to send acknowledgement to
    :param database_notify_host: host IP to send notification to
    :param database_notify_port_num: port that the external device will be\
        notified on.
    """
    database_socket = SocketAddress(
        listen_port=database_ack_port_num,
        notify_host_name=database_notify_host,
        notify_port_no=database_notify_port_num)

    _sim().add_socket_address(database_socket)


def get_txrx():
    """ Gets the transceiver used by the tool chain.
    """
    return _sim().transceiver


def get_number_of_available_cores_on_machine():
    """ Gets the number of cores on this machine that are available to the\
        simulation.
    """
    return _sim().get_number_of_available_cores_on_machine


def has_ran():
    return _sim().has_ran


def machine_time_step():
    return _sim().machine_time_step


def no_machine_time_steps():
    return _sim().no_machine_time_steps


def time_scale_factor():
    return _sim().time_scale_factor


def machine_graph():
    return _sim().machine_graph


def application_graph():
    return _sim().application_graph


def routing_infos():
    return _sim().routing_infos


def placements():
    return _sim().placements


def transceiver():
    return _sim().transceiver


def tags():
    return _sim().tags


def graph_mapper():
    return _sim().graph_mapper


def buffer_manager():
    """
    :return: the buffer manager being used for loading/extracting buffers
    """
    return _sim().buffer_manager


def machine():
    logger.warning(
        "If you are getting the machine object to locate how many cores you "
        "can use,\n"
        "please use the following function call, as it is more reliable and "
        "takes into account software resources as well:\n\n"
        "get_number_of_available_cores_on_machine()")
    return _sim().machine


def is_allocated_machine():
    return _sim().is_allocated_machine


def use_virtual_machine():
    return _sim().use_virtual_board
