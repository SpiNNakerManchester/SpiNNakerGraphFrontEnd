from spinn_front_end_common.utilities.utility_objs import ExecutableFinder
from spinnaker_graph_front_end.examples.nengo.nengo_components.connection import \
    Connection
from spinnaker_graph_front_end.examples.nengo.nengo_components.ensemble import \
    Ensemble
from spinnaker_graph_front_end.spinnaker import SpiNNaker
from spinnaker_graph_front_end.examples.nengo import binaries

from spinnaker_graph_front_end.examples.nengo.nengo_components.node import Node

import logging
import os
import numpy
import nengo

logger = logging.getLogger(__name__)


class NengoSimulator(SpiNNaker):
    """SpiNNaker simulator for Nengo models.

    The simulator period determines how much data will be stored on SpiNNaker
    and is the maximum length of simulation allowed before data is transferred
    between the machine and the host PC. 
    
    For any other value simulation lengths of less than or equal to the period
    will be in real-time, longer simulations will be possible but will include
    short gaps when data is transferred between SpiNNaker and the host.

    :py:meth:`~.close` should be called when the simulator will no longer be
    used. This will close all sockets used to communicate with the SpiNNaker
    machine and will leave the machine in a clean state. Failure to call
    `close` may result in later failures. Alternatively `with` may be used::

        sim = nengo_spinnaker.Simulator(network)
        with sim:
            sim.run(10.0)
    """

    __slots__ = []

    def __init__(
            self, network, dt=0.001, time_scale=1.0,
            host_name=None, graph_label=None,
            database_socket_addresses=None, dsg_algorithm=None,
            n_chips_required=None, extra_pre_run_algorithms=None,
            extra_post_run_algorithms=None):
        """Create a new Simulator with the given network.
        
        :param time_scale: Scaling factor to apply to the simulation, e.g.,\
            a value of `0.5` will cause the simulation to run at twice \
            real-time.
        :type time_scale: float
        :param host_name: Hostname of the SpiNNaker machine to use; if None\  
            then the machine specified in the config file will be used.
        :type host_name: basestring or None
        :param dt: The length of a simulator timestep, in seconds.
        :type dt: float
        :param graph_label: human readable graph label
        :type graph_label: basestring
        :param database_socket_addresses:
        :type database_socket_addresses:
        :param dsg_algorithm:
        :type dsg_algorithm:
        :param n_chips_required:
        :type n_chips_required:
        :param extra_post_run_algorithms:
        :type extra_post_run_algorithms:
        :param extra_pre_run_algorithms:
        :type extra_pre_run_algorithms:
        :rtype None
        """
        executable_finder = ExecutableFinder()
        executable_finder.add_path(os.path.dirname(binaries.__file__))

        # Calculate the machine timestep, this is measured in microseconds
        # (hence the 1e6 scaling factor).
        machine_timestep = int((dt / time_scale) * 1e6)

        SpiNNaker.__init__(
            self, executable_finder, host_name=host_name,
            graph_label=graph_label,
            database_socket_addresses=database_socket_addresses,
            dsg_algorithm=dsg_algorithm,
            n_chips_required=n_chips_required,
            extra_pre_run_algorithms=extra_pre_run_algorithms,
            extra_post_run_algorithms=extra_post_run_algorithms,
            time_scale_factor=time_scale,
            machine_time_step=machine_timestep)

        # create nengo to spinnaker nengo component map
        model_conversion_map = dict()
        model_conversion_map[nengo.node.Node] = Node
        model_conversion_map[nengo.ensemble.Ensemble] = Ensemble
        model_conversion_map[nengo.connection.Connection] = Connection

        self.update_extra_inputs(
            {'NengoModel': network,
             'NengoMap': model_conversion_map,
             "NengoNodeIOSetting": self.config.get("Simulator", "node_io"),
             "NengoNodeSetAsFunctionOfTime":
                 self.config.getboolean("Node", "function_of_time"),
             "NengoNodeSetAsFunctionOfTimePeriod":
                 self.config.getboolean("Node", "function_of_time_period"),
             "NengoNodeOptimizeOut":
                 self.config.getboolean("Node", "optimise_out"),
             "NengoEnsembleProfile":
                 self.config.getboolean("Ensemble", "profile"),
             "NengoEnsembleProfileNumSamples":
                 self.config.getboolean("Ensemble", "profile_num_samples"),
             "NengoRandomNumberGeneratorSeed":
                self.config.get("Simulator", "global_seed")})

    def __enter__(self):
        """Enter a context which will close the simulator when exited."""
        # Return self to allow usage like:
        #
        #     with nengo_spinnaker.Simulator(model) as sim:
        #         sim.run(1.0)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Exit a context and close the simulator."""
        self.close()

    def run(self, time_in_seconds):
        """Simulate for the given length of time."""
        # Determine how many steps to simulate for
        steps = int(numpy.round(float(time_in_seconds) / self.dt))
        self.run_steps(steps)

    def run_steps(self, steps):
        """Simulate a give number of steps."""
        while steps > 0:
            n_steps = min((steps, self.max_steps))
            self._run_steps(n_steps)
            steps -= n_steps

    def _run_steps(self, steps):
        """Simulate for the given number of steps."""
        SpiNNaker.run(self, steps)

        # extract data
        self._extract_data()

    def close(self, turn_off_machine=None, clear_routing_tables=None,
              clear_tags=None):
        """Clean the SpiNNaker board and prevent further simulation."""
        if not self._closed:
            self.io_controller.close()
            self.controller.send_signal("stop")
            SpiNNaker.stop(
                self=self, turn_off_machine=turn_off_machine,
                clear_tags=clear_tags,
                clear_routing_tables=clear_routing_tables)
