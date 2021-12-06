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

"""
The API for running SpiNNaker simulations based on a basic (non-neural) graph.

The general usage pattern for this API something like is::

    import spinnaker_graph_front_end as gfe

    # Uses information from your configuration file
    # You might need to specify how many SpiNNaker boards to allocate
    gfe.setup()

    # Make the bits that do the computation
    for each vertex to add:
        gfe.add_machine_vertex_instance(vertex)

    # Connect them together so computations are coordinated
    for each edge to add:
        gfe.add_machine_edge_instance(edge)

    # Actually plan and run the simulation
    gfe.run(number_of_steps)

    # Get the results back; what this means can be complex
    for each vertex:
        results += vertex.retrieve_relevant_results()

    # Shut everything down
    # Only your retrieved results really exist after this
    gfe.stop()

    # Analyse/render the results; totally application-specific!

It is possible to use GFE-style vertices in a neural graph (e.g., to simulate
the external world). Talk to the SpiNNaker team for more details.
"""

import os
import logging
import sys
from spinn_utilities.log import FormatAdapter
from spinn_utilities.socket_address import SocketAddress
from pacman.model.graphs.application import ApplicationEdge, ApplicationVertex
from pacman.model.graphs.machine import MachineEdge as _ME, MachineVertex
from spinn_front_end_common.utilities.utility_objs import ExecutableFinder
from spinn_front_end_common.utilities import globals_variables
from spinn_front_end_common.utility_models import (
    LivePacketGather as
    _LPG, ReverseIpTagMultiCastSource as
    _RIPTMCS)
from spinnaker_graph_front_end._version import (
    __version__, __version_name__, __version_month__, __version_year__)
from spinnaker_graph_front_end.spinnaker import SpiNNaker
from spinnaker_graph_front_end import spinnaker as gfe_file

logger = FormatAdapter(logging.getLogger(__name__))


__all__ = ['LivePacketGather', 'ReverseIpTagMultiCastSource', 'MachineEdge',
           'setup', 'run', 'stop', 'read_xml_file', 'add_vertex_instance',
           'add_vertex', 'add_machine_vertex', 'add_machine_vertex_instance',
           'add_edge', 'add_application_edge_instance', 'add_machine_edge',
           'add_machine_edge_instance', 'add_socket_address', 'get_txrx',
           'has_ran', 'get_number_of_available_cores_on_machine',
           'machine_graph', 'application_graph',
           'routing_infos', 'placements', 'transceiver',
           'buffer_manager', 'machine', 'is_allocated_machine']


def setup(hostname=None, graph_label=None, model_binary_module=None,
          model_binary_folder=None, database_socket_addresses=(),
          n_chips_required=None, n_boards_required=None,
          time_scale_factor=None, machine_time_step=None):
    """ Set up a graph, ready to have vertices and edges added to it, and the\
        simulator engine that will execute the graph.

    .. note::
        This must be called *before* the other functions in this API.

    :param str hostname:
        the hostname of the SpiNNaker machine to operate on
        (overrides the ``machine_name`` from the cfg file).
    :param str graph_label:
        a human readable label for the graph (used mainly in reports)
    :param ~types.ModuleType model_binary_module:
        the Python module where the binary files (``.aplx``) can be found for
        the compiled C code that is being used in this application; mutually
        exclusive with the ``model_binary_folder``.
    :param str model_binary_folder:
        the folder where the binary files can be found for the c code that is
        being used in this application; mutually exclusive with the
        ``model_binary_module``.
    :param database_socket_addresses:
        set of SocketAddresses to be added for the database notification
        system. These are over and above the ones used by the
        :py:class:`~spinn_front_end_common.utilities.connections.LiveEventConnection`
    :type database_socket_addresses:
        ~collections.abc.Iterable(~spinn_utilities.socket_address.SocketAddress)
    :param n_chips_required:
        Deprecated! Use ``n_boards_required`` instead.
        Must be ``None`` if ``n_boards_required`` specified.
    :type n_chips_required: int or None
    :param n_boards_required:
        if you need to be allocated a machine (for spalloc) before building
        your graph, then fill this in with a general idea of the number of
        boards you need so that the spalloc system can allocate you a machine
        big enough for your needs.
    :type n_boards_required: int or None
    :raise ~spinn_front_end_common.utilities.exceptions.ConfigurationException:
        if mutually exclusive options are given.
    """
    # pylint: disable=redefined-outer-name
    logger.info(
        "SpiNNaker graph front end (c) {}, University of Manchester",
        __version_year__)
    parent_dir = os.path.split(os.path.split(gfe_file.__file__)[0])[0]
    logger.info(
        "Release version {}({}) - {} {}. Installed in folder {}",
        __version__, __version_name__, __version_month__, __version_year__,
        parent_dir)

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

    # set up the spinnaker object; after this, _sim() returns this object
    SpiNNaker(
        host_name=hostname, graph_label=graph_label,
        executable_finder=executable_finder,
        database_socket_addresses=database_socket_addresses,
        n_chips_required=n_chips_required,
        n_boards_required=n_boards_required,
        machine_time_step=machine_time_step,
        time_scale_factor=time_scale_factor)


def _sim():
    """ Get the current SpiNNaker simulator object.

    :rtype: ~spinn_front_end_common.utilities.SimulatorInterface
    """
    return globals_variables.get_simulator()


def run(duration=None):
    """ Run a simulation for a number of microseconds.

    :param int duration:
        the number of microseconds the application code should run for
    """
    _sim().run(duration)


def run_until_complete(n_steps=None):
    """ Run until the simulation is complete.

    :param int n_steps:
        If not ``None``, this specifies that the simulation should be
        requested to run for the given number of steps.  The host will
        still wait until the simulation itself says it has completed
    """
    _sim().run_until_complete(n_steps)


def stop():
    """ Do any necessary cleaning up before exiting. Unregisters the controller
    """
    # pylint: disable=global-variable-undefined
    global _executable_finder

    _sim().stop()
    _executable_finder = None


def stop_run():
    """ Stop a request to run forever
    """
    _sim().stop_run()


def read_xml_file(file_path):
    """ Read an XML file containing a graph description and translate it into\
        an application graph and machine graph (if required).

    .. warning::
        This is not officially supported functionality yet.

    :param str file_path: the file path in absolute form
    """
    logger.warning("This functionality is not yet supported")
    _sim().read_xml_file(file_path)


def add_vertex(cell_class, cell_params, label=None, constraints=()):
    """ Create an application vertex and add it to the unpartitioned graph.

    :param type cell_class:
        the class object for creating the application vertex
    :param dict(str,object) cell_params:
        the input parameters for the class object
    :param label: the label for this vertex
    :type label: str or None
    :param constraints:
        any constraints to be applied to the vertex once built
    :type constraints:
        ~collections.abc.Iterable(~pacman.model.constraints.AbstractConstraint)
    :return: the application vertex instance object
    :rtype: ~pacman.model.graphs.application.ApplicationVertex
    """
    if not issubclass(cell_class, ApplicationVertex):
        raise TypeError(f"{cell_class} is not an application vertex class")
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

    :param ~pacman.model.graphs.application.ApplicationVertex vertex_to_add:
        vertex instance to add to the graph
    """
    _sim().add_application_vertex(vertex_to_add)


def add_machine_vertex(
        cell_class, cell_params, label=None, constraints=()):
    """ Create a machine vertex and add it to the partitioned graph.

    :param type cell_class:
        the class of the machine vertex to create
    :param dict(str,object) cell_params:
        the input parameters for the class object
    :param label:
        the label for this vertex
    :type label: str or None
    :param constraints:
        any constraints to be applied to the vertex once built
    :type constraints:
        ~collections.abc.Iterable(~pacman.model.constraints.AbstractConstraint)
    :return: the machine vertex instance object
    :rtype: ~pacman.model.graphs.machine.MachineVertex
    """
    if not issubclass(cell_class, MachineVertex):
        raise TypeError(f"{cell_class} is not a machine vertex class")
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

    :param ~pacman.model.graphs.machine.MachineVertex vertex_to_add:
        the vertex to add to the partitioned graph
    """
    _sim().add_machine_vertex(vertex_to_add)


def _new_edge_label():
    sim = _sim()
    label = f"Edge {sim.none_labelled_edge_count}"
    sim.increment_none_labelled_edge_count()
    return label


def add_edge(edge_type, edge_parameters, semantic_label, label=None):
    """ Create an application edge and add it to the unpartitioned graph.

    :param type edge_type:
        the kind (class) of application edge to create
    :param dict(str,object) edge_parameters:
        parameters to pass to the constructor
    :param str semantic_label:
        the ID of the partition that the edge belongs to
    :param str label:
        textual label for the edge, or None
    :return: the created application edge
    :rtype: ~pacman.model.graphs.application.ApplicationEdge
    """
    if not issubclass(edge_type, ApplicationEdge):
        raise TypeError(f"{edge_type} is not an application edge class")
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
    """ Add an edge to the unpartitioned graph.

    :param ~pacman.model.graphs.application.ApplicationEdge edge:
        The edge to add.
    :param str partition_id:
        The ID of the partition that the edge belongs to.
    """
    _sim().add_application_edge(edge, partition_id)


def add_machine_edge(edge_type, edge_parameters, semantic_label, label=None):
    """ Create a machine edge and add it to the partitioned graph.

    :param type edge_type:
        the kind (class) of machine edge to create
    :param dict(str,object) edge_parameters:
        parameters to pass to the constructor
    :param str semantic_label:
        the ID of the partition that the edge belongs to
    :param str label:
        textual label for the edge, or None
    :return: the created machine edge
    :rtype: ~pacman.model.graphs.machine.MachineEdge
    """
    if not issubclass(edge_type, _ME):
        raise TypeError(f"{edge_type} is not a machine edge class")
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
    """ Add an edge to the partitioned graph.

    :param ~pacman.model.graphs.machine.MachineEdge edge:
        The edge to add.
    :param str partition_id:
        The ID of the partition that the edge belongs to.
    """
    _sim().add_machine_edge(edge, partition_id)


def add_socket_address(
        database_ack_port_num, database_notify_host, database_notify_port_num):
    """ Add a socket address for the notification protocol.

    :param int database_ack_port_num:
        port number to send acknowledgement to
    :param str database_notify_host:
        host IP to send notification to
    :param int database_notify_port_num:
        port that the external device will be notified on.
    """
    database_socket = SocketAddress(
        listen_port=database_ack_port_num,
        notify_host_name=database_notify_host,
        notify_port_no=database_notify_port_num)

    _sim().add_socket_address(database_socket)


def get_txrx():
    """ Get the transceiver used by the tool chain.

    :rtype: ~spinnman.transceiver.Transceiver
    """
    return _sim().transceiver


def get_number_of_available_cores_on_machine():
    """ Get the number of cores on this machine that are available to the\
        simulation.

    :rtype: int
    """
    return _sim().get_number_of_available_cores_on_machine


def has_ran():
    """ Get whether the simulation has already run.

    :rtype: bool
    """
    return _sim().has_ran


def routing_infos():
    """ Get information about how messages are routed on the machine.

    :rtype: ~pacman.model.routing_info.RoutingInfo
    """
    return _sim().routing_infos


def placements():
    """ Get the planned locations of machine vertices on the machine.

    :rtype: ~pacman.model.placements.Placements
    """
    return _sim().placements


def transceiver():
    """ Get the transceiver, for talking directly to the SpiNNaker system.

    :rtype: ~spinnman.transceiver.Transceiver
    """
    return _sim().transceiver


def tags():
    """ Get the IPTAGs allocated on the machine.

    :rtype: ~pacman.model.tags.Tags
    """
    return _sim().tags


def buffer_manager():
    """ Get the buffer manager being used for loading/extracting buffers

    :rtype: ~spinn_front_end_common.interface.buffer_management.BufferManager
    """
    return _sim().buffer_manager


def machine():
    """ Get the model of the attached/allocated machine.

    :rtype: ~spinn_machine.Machine
    """
    logger.warning(
        "If you are getting the machine object to locate how many cores you "
        "can use,\n"
        "please use the following function call, as it is more reliable and "
        "takes into account software resources as well:\n\n"
        "get_number_of_available_cores_on_machine()")
    return _sim().machine


def is_allocated_machine():
    """ Get whether a machine is allocated.

    :rtype: bool
    """
    return _sim().is_allocated_machine


def use_virtual_machine():
    """ Get whether a virtual machine is being used.

    .. note::
        Virtual machines cannot execute any programs.
        However, they can be used to check whether code can be deployed.

    :rtype: bool
    """
    return _sim().use_virtual_board


# Thin wrappers for documentation purposes only
class MachineEdge(_ME):
    """
    For full documentation see
    :py:class:`~pacman.model.graphs.machine.MachineEdge`.
    """
    __slots__ = ()


class LivePacketGather(_LPG):
    """
    For full documentation see
    :py:class:`~spinn_front_end_common.utility_models.LivePacketGather`.
    """
    __slots__ = ()


class ReverseIpTagMultiCastSource(_RIPTMCS):
    """
    For full documentation see
    :py:class:`~spinn_front_end_common.utility_models.ReverseIpTagMultiCastSource`.
    """
    __slots__ = ()
