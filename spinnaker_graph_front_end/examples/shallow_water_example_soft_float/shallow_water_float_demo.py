import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.shallow_water_example_soft_float.\
    debug_functions import DebugCalls
from spinnaker_graph_front_end.examples.shallow_water_example_soft_float. \
    shallow_water_edge import ShallowWaterEdge

from spinnaker_graph_front_end.examples.shallow_water_example_soft_float. \
    shallow_water_vertex import ShallowWaterVertex

import math
import logging

logger = logging.getLogger(__name__)

# grid size
# MAX_X_SIZE_OF_FABRIC = 64
# MAX_Y_SIZE_OF_FABRIC = 64
MAX_X_SIZE_OF_FABRIC = 3
MAX_Y_SIZE_OF_FABRIC = 3

# tdma constants
NumberOfCPUCyclesUsedByThePacketReceiveCallback = 2000
NumberOfCpuCyclesByOtherCallbacks = 600
NumberOFPacketsPerWindow = 4
FUDGE_FACTOR_FOR_TDMA = 2

# read in from file the initial params (fixes c generation issues)
READ_IN_FROM_FILE = True
RUN_FROM_SCRIPT = False

# timing
# super fast,. not recording
# MACHINE_TIME_STEP_IN_MICRO_SECONDS = 120
# TIME_SCALE_FACTOR = 1

# recording
MACHINE_TIME_STEP_IN_MICRO_SECONDS = 10000
TIME_SCALE_FACTOR = 20

# machine assumptions
CORES_PER_CHIP = 16

# runtime
#RUNTIME = 4000
RUNTIME = 30


class WeatherRun(object):
    """
    weather network holder. creates the network for SpiNNaker.
    """

    def __init__(self):

        self._debug_calls = DebugCalls()

        self._DT, self._TDT, self._DX, self._DY, self._FSDX, self._FSDY,\
        self._A, self._ALPHA, self._EL, self._PI, self._TPI, self._DI, \
        self._DJ, self._PCF, self._tdts8, self._tdtsdx, self._tdtsdy, \
        self._tdt2s8, self._tdt2sdx, self._tdt2sdy = \
            self._debug_calls.read_in_constants()

        if RUN_FROM_SCRIPT:
            self._debug_calls.run_orginial_c_code(
                MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)

        # print the constants
        self._debug_calls.print_constants(
            self._DT, self._TDT, self._DX, self._DY, self._FSDX, self._FSDY,
            self._A, self._ALPHA, self._EL, self._PI, self._TPI, self._DI,
            self._DJ, self._PCF, self._tdts8, self._tdtsdx, self._tdtsdy,
            self._tdt2s8, self._tdt2sdx, self._tdt2sdy)

        # figure machine size needed at a min
        min_chips = \
            (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC) / CORES_PER_CHIP

        # set up the front end and ask for the detected machines dimensions
        front_end.setup(
            machine_time_step=MACHINE_TIME_STEP_IN_MICRO_SECONDS,
            time_scale_factor=TIME_SCALE_FACTOR,
            n_chips_required=min_chips, end_user_extra_mapping_inputs={
                'NumberOfCPUCyclesUsedByThePacketReceiveCallback':
                    NumberOfCPUCyclesUsedByThePacketReceiveCallback,
                'NumberOfCpuCyclesByOtherCallbacks':
                    NumberOfCpuCyclesByOtherCallbacks,
                'NPacketsPerTimeWindow': NumberOFPacketsPerWindow,
                'EndUserConfigurableSafetyFactorForTDMAAgenda':
                    FUDGE_FACTOR_FOR_TDMA})

        # contain the vertices for the connection aspect
        self._vertices = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

        # handle read in if needed
        if READ_IN_FROM_FILE:
            self._read_in_psi = self._debug_calls.read_in_psi_from_file(
                MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)
            self._read_in_u = self._debug_calls.read_in_u_from_file(
                MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)
            self._read_in_v = self._debug_calls.read_in_v_from_file(
                MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)
            self._read_in_p = self._debug_calls.read_in_p_from_file(
                MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)

        # handle the psi value generation
        self._psi = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC + 1)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC + 1)]
        self._sort_out_psi()

        # handle mass flux velocity in different directions
        self._mass_flux_u = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC + 1)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC + 1)]
        self._sort_out_u()
        self._mass_flux_v = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC + 1)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC + 1)]
        self._sort_out_v()

        # print out initial values for verification purposes
        self._debug_calls.print_initial_values(
            MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC, self._psi)

        # build vertices
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                p = self._pressure_calculation(x, y)
                u = self._mass_flux_u[x][y]
                v = self._mass_flux_v[x][y]

                vert = ShallowWaterVertex(
                    p=p, u=u, v=v, x=x, y=y,
                    tdt=self._TDT, dx=self._DX, dy=self._DY, fsdx=self._FSDX,
                    fsdy=self._FSDY, alpha=self._ALPHA, tdts8=self._tdts8,
                    tdtsdx=self._tdt2sdx, tdtsdy=self._tdt2sdy,
                    tdt2s8=self._tdt2s8, tdt2sdx=self._tdt2sdx,
                    tdt2sdy=self._tdt2sdy,
                    label="weather_vertex{}:{}".format(x, y))

                self._vertices[x][y] = vert
                front_end.add_machine_vertex_instance(vert)

        #logger.info("vertex bits before periodic")

        self._debug_calls.print_vertex_bits(
            MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC, self._vertices)

        #self._do_periodic_continuation(
        #    MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC, self._vertices)

        #logger.info("vertex bits after periodic")

        #self._debug_calls.print_vertex_bits(
        #    MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC, self._vertices)

        # build edges
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._build_edges_for_vertex(x, y)

        self._debug_calls.verify_graph_setup_properly(
            self._vertices, MAX_X_SIZE_OF_FABRIC,
            MAX_Y_SIZE_OF_FABRIC)

        self._debug_calls.print_vertex_bits(
            MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC, self._vertices)

    def _do_periodic_continuation(
            self, max_x_size_of_fabric, max_y_size_of_fabric, vertices):
        """ does the wrap around functionality. needed as the first u and vs 
        are wrapped before the evolution
        
        :param max_x_size_of_fabric: size of fabric in x axis
        :param max_y_size_of_fabric: size of fabric in y axis
        :param vertices: array of vertices
        :return: None
        """
        for j in range(0, max_y_size_of_fabric - 1):
            vertices[0][j].u = vertices[
                max_x_size_of_fabric - 1][j].u
            vertices[max_y_size_of_fabric - 1][
                (j + 1) % max_y_size_of_fabric].v = \
                vertices[0][(j + 1) % max_y_size_of_fabric].v
        for i in range(0, max_x_size_of_fabric - 1):
            vertices[(i + 1) % max_y_size_of_fabric][
                max_x_size_of_fabric - 1].u = vertices[
                (i + 1) % max_y_size_of_fabric][0].u
            vertices[i][0].v = vertices[0][
                max_y_size_of_fabric - 1].v

        vertices[0][max_y_size_of_fabric - 1].u = vertices[
            max_x_size_of_fabric - 1][0].u
        vertices[max_x_size_of_fabric - 1][0].v = vertices[
            0][max_y_size_of_fabric - 1].v

    def _sort_out_psi(self):
        """ calculates the psi values for each atom

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                if READ_IN_FROM_FILE:
                    self._psi[x][y] = self._read_in_psi[x][y]
                else:
                    self._psi[x][y] = self._psi_calculation(x, y)

    def _sort_out_u(self):
        """calculates the u values for each atom

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                if READ_IN_FROM_FILE:
                    self._mass_flux_u[x][y] = self._read_in_u[x][y]
                else:
                    self._mass_flux_u[x][y] = \
                        self._mass_flux_u_calculation(x, y, self._psi)

    def _sort_out_v(self):
        """calculates the u values for each atom

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                if READ_IN_FROM_FILE:
                    self._mass_flux_v[x][y] = self._read_in_v[x][y]
                else:
                    self._mass_flux_v[x][y] = \
                        self._mass_flux_v_calculation(x, y, self._psi)

    def _build_edges_for_vertex(self, x, y):
        """ for a given vertex, builds the edges that communicate
        different data types

        :param x: the vertex in x dimension
        :param y: the vertex in y dimension
        :return: None
        """

        # the 8 positions from neighbours
        positions = [
            ((x + 1) % MAX_X_SIZE_OF_FABRIC, y, "N"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
             (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NE"),
            (x, (y + 1) % MAX_Y_SIZE_OF_FABRIC, "E"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
             (y + 1) % MAX_Y_SIZE_OF_FABRIC, "SE"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC, y, "S"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
             (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SW"),
            (x, (y - 1) % MAX_Y_SIZE_OF_FABRIC, "W"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
             (y - 1) % MAX_Y_SIZE_OF_FABRIC, "NW")]

        logger.info("positions {}:{} = {}".format(x, y, positions))

        # build edges for each direction for this vertex
        for (dest_x, dest_y, compass) in positions:
            front_end.add_machine_edge_instance(ShallowWaterEdge(
                self._vertices[x][y], self._vertices[dest_x][dest_y],
                compass, "edge between {} and {}".format(
                    self._vertices[x][y], self._vertices[dest_x][dest_y])),
                ShallowWaterVertex.ROUTING_PARTITION)
            self._vertices[x][y].set_direction_vertex(
                direction=compass, vertex=self._vertices[dest_x][dest_y])

    def _psi_calculation(self, x, y):
        """ creates the psi calculation

        :param x: the x coord of the vertex to make a psi of
        :param y: the y coord of the vertex to make a psi of
        :return: the psi calculation
        """
        # a * sin((i + .5) * di) * sin((j + .5) * dj);

        sinx = math.sin((x + 0.5) * self._DI)
        siny = math.sin((y + 0.5) * self._DJ)
        total = self._A * sinx * siny
        logger.info(
            "psi {}{}, sinx {} siny {:20.16f} total {}".format(
                x, y, sinx, siny, total))
        return self._A * math.sin((x + 0.5) * self._DI) * \
               math.sin((y + 0.5) * self._DJ)

    def _pressure_calculation(self, x, y):
        """ creates the p calculation

        :param x: the x coord of the vertex to make a p of
        :param y: the y coord of the vertex to make a p of
        :return: the p calculation
        """
        if READ_IN_FROM_FILE:
            return self._read_in_p[x][y]
        else:
            return self._PCF * (math.cos(2.0 * x * self._DI) +
                          math.cos(2.0 * y * self._DJ)) + 50000.0

    def _mass_flux_u_calculation(self, x, y, psi):
        """ creates the u calculation

        :param x: the x coord of the vertex to make a u of
        :param y: the y coord of the vertex to make a u of
        :return: the u calculation
        """
        return -(psi
                 [(x % MAX_X_SIZE_OF_FABRIC)]
                 [((y + 1) % MAX_Y_SIZE_OF_FABRIC)] -
                 psi
                 [(x % MAX_X_SIZE_OF_FABRIC)]
                 [(y % MAX_Y_SIZE_OF_FABRIC)]) / self._DY

    def _mass_flux_v_calculation(self, x, y, psi):
        """ creates the v calculation

        :param x: the x coord of the vertex to make a v of
        :param y: the y coord of the vertex to make a v of
        :return: the v calculation
        """
        return (psi
                [((x + 1) % MAX_X_SIZE_OF_FABRIC)]
                [(y % MAX_Y_SIZE_OF_FABRIC)] -
                psi
                [(x % MAX_X_SIZE_OF_FABRIC)]
                [(y % MAX_Y_SIZE_OF_FABRIC)]) / self._DX

    @staticmethod
    def run(runtime):
        """ runs the network for a given simulation time in ms

        :param runtime: the runtime in ms
        :return: None
        """
        # run the simulation
        front_end.run(runtime)

    def print_diagonal_data(self, recorded_data):
        """ print the messages c code does at end

        :param recorded_data: the recorded data
        :return: None
        """
        self._debug_calls.print_diagonal_data(
            recorded_data, MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC,
            RUNTIME, self._DT)

    def extract_data(self):
        """ extracts data from the machine

        :return: data as a dict of [param][time]
        """
        # get recorded data
        recorded_data = dict()

        # get the data per vertex
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                recorded_data[(x, y)] = self._vertices[x][y].get_data(
                    front_end.buffer_manager(),
                    front_end.placements().get_placement_of_vertex(
                        self._vertices[x][y]))
        return recorded_data

    def print_init_states(self):
        self._debug_calls.print_init_states(
            MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC,
            self._DX, self._DY, self._DT, self._ALPHA, self._vertices)

    def print_all_data(self, recorded_data):
        self._debug_calls.print_all_data(
            recorded_data, RUNTIME, MAX_X_SIZE_OF_FABRIC,
            MAX_Y_SIZE_OF_FABRIC)

    @staticmethod
    def stop():
        # clear the machine
        front_end.stop()

if __name__ == "__main__":
    """
    main entrance method
    """
    # create network
    run = WeatherRun()

    # print init states
    run.print_init_states()

    # run sim
    run.run(RUNTIME)

    # extract data from machine
    ##data = run.extract_data()

    # print data to screen
    ##run.print_all_data(data)
    # run.print_diagonal_data(data)

    # finish sim on machine. basically clean up for future sims.
    run.stop()
