from nengo.cache import NoDecoderCache
from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.utilities.utility_objs import ExecutableFinder
from spinnaker_graph_front_end.examples.nengo.utility_objects.\
    nengo_application_graph_generator import \
    NengoApplicationGraphGenerator
from spinnaker_graph_front_end.examples.nengo \
    import overridden_mapping_algorithms
from spinnaker_graph_front_end.spinnaker import SpiNNaker
from spinnaker_graph_front_end.examples.nengo import binaries, constants

import logging
import os
import numpy

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

    __slots__ = [
    ]

    CONFIG_FILE_NAME = "nengo_spinnaker.cfg"
    NENGO_ALGORITHM_XML_FILE_NAME = "nengo_overridden_mapping_algorithms.xml"

    def __init__(
            self, network, dt=constants.DEFAULT_DT,
            time_scale=constants.DEFAULT_TIME_SCALE,
            host_name=None, graph_label=None,
            database_socket_addresses=None, dsg_algorithm=None,
            n_chips_required=None, extra_pre_run_algorithms=None,
            extra_post_run_algorithms=None, decoder_cache=NoDecoderCache(),
            function_of_time_nodes=None,
            function_of_time_nodes_time_period=None):
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
        values
        :rtype None
        """
        executable_finder = ExecutableFinder()
        executable_finder.add_path(os.path.dirname(binaries.__file__))

        # Calculate the machine timestep, this is measured in microseconds
        # (hence the 1e6 scaling factor).
        machine_time_step = (
            int((dt / time_scale) *
                constants.SECONDS_TO_MICRO_SECONDS_CONVERTER))

        xml_paths = list()
        xml_paths.append(os.path.join(os.path.dirname(
            overridden_mapping_algorithms.__file__),
            self.NENGO_ALGORITHM_XML_FILE_NAME))

        SpiNNaker.__init__(
            self, executable_finder, host_name=host_name,
            graph_label=graph_label,
            database_socket_addresses=database_socket_addresses,
            dsg_algorithm=dsg_algorithm,
            n_chips_required=n_chips_required,
            extra_pre_run_algorithms=extra_pre_run_algorithms,
            extra_post_run_algorithms=extra_post_run_algorithms,
            time_scale_factor=time_scale,
            default_config_paths=(
                os.path.join(os.path.dirname(__file__),
                             self.CONFIG_FILE_NAME)),
            machine_time_step=machine_time_step,
            extra_xml_paths=xml_paths)

        # basic mapping extras
        extra_mapping_algorithms = [
            "NengoKeyAllocator", "NengoHostGraphUpdateBuilder",
            "NengoCreateHostSimulator", "NengoSetUpLiveIO"]

        if function_of_time_nodes is None:
            function_of_time_nodes = list()
        if function_of_time_nodes_time_period is None:
            function_of_time_nodes_time_period = list()

        # update the main flow with new algorithms and params
        self.extend_extra_mapping_algorithms(extra_mapping_algorithms)
        self.update_extra_inputs(
            {'NengoNodesAsFunctionOfTime': function_of_time_nodes,
             'NengoNodesAsFunctionOfTimeTimePeriod':
                 function_of_time_nodes_time_period,
             'NengoModel': network,
             'NengoDecoderCache': decoder_cache,
             "NengoNodeIOSetting": self.config.get("Simulator", "node_io"),
             "NengoEnsembleProfile":
                 self.config.getboolean("Ensemble", "profile"),
             "NengoEnsembleProfileNumSamples":
                 helpful_functions.read_config_int(
                     self.config, "Ensemble", "profile_num_samples"),
             "NengoRandomNumberGeneratorSeed":
                helpful_functions.read_config_int(
                    self.config, "Simulator", "global_seed"),
             "NengoUtiliseExtraCoreForProbes":
                self.config.getboolean(
                    "Node", "utilise_extra_core_for_probes"),
             "MachineTimeStepInSeconds": dt})

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
        steps = int(
            numpy.round(
                float((time_in_seconds *
                       constants.SECONDS_TO_MICRO_SECONDS_CONVERTER))
                / self.machine_time_step))
        self._run_steps(steps)

    def _run_steps(self, steps):
        """Simulate for the given number of steps."""

        # build app graph, as the main tools expect an application / machine
        # graph level, and cannot go from random to app graph.
        nengo_app_graph_generator = NengoApplicationGraphGenerator()
        (nengo_operator_graph, host_network, nengo_to_app_graph_map,
         random_number_generator) = \
            nengo_app_graph_generator(
                self._extra_inputs["NengoModel"], self.machine_time_step,
                self._extra_inputs["NengoRandomNumberGeneratorSeed"],
                self._extra_inputs["NengoDecoderCache"],
                self._extra_inputs["NengoUtiliseExtraCoreForProbes"],
                self._extra_inputs["NengoNodesAsFunctionOfTime"],
                self._extra_inputs["NengoNodesAsFunctionOfTimeTimePeriod"],
                self.config.getboolean("Node", "optimise_utilise_interposers"))

        # update spinnaker with app graph
        self._original_application_graph = nengo_operator_graph

        # add the extra outputs as new inputs
        self.update_extra_inputs(
            {"NengoHostGraph": host_network,
             "NengoGraphToAppGraphMap": nengo_to_app_graph_map,
             "NengoRandomNumberGenerator": random_number_generator})

        # run the rest of the tools
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
