import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.weather_example.weather_edge import \
    WeatherDemoEdge

from spinnaker_graph_front_end.examples.weather_example.weather_vertex \
    import WeatherVertex

import math
import logging

logger = logging.getLogger(__name__)

# grid size
#MAX_X_SIZE_OF_FABRIC = 64
#MAX_Y_SIZE_OF_FABRIC = 64
MAX_X_SIZE_OF_FABRIC = 3
MAX_Y_SIZE_OF_FABRIC = 3

# runtime
#RUNTIME = 4000
RUNTIME = 30

# random state variable inits
DT = 90.0
TDT = DT
DX = 100000.0
DY = 100000.0
FSDX = round(4.0 / DX, 6)
FSDY = round(4.0 / DY, 6)
A = 1000000.0
ALPHA = 0.001
EL = MAX_Y_SIZE_OF_FABRIC * DX
PI_UNROUNDED = 4.0 * math.atan(float(1.0))
PI = round(PI_UNROUNDED, 6)
TPI = round(PI_UNROUNDED + PI_UNROUNDED, 6)
DI = round(TPI / MAX_X_SIZE_OF_FABRIC, 6)
DJ = round(TPI / MAX_Y_SIZE_OF_FABRIC, 6)
PCF = round(PI_UNROUNDED * PI_UNROUNDED * A * A / (EL * EL), 6)



class WeatherRun(object):
    """
    weather network holder. creates the network for SpiNNaker.
    """

    def __init__(self):
        machine_time_step = 1000
        time_scale_factor = 10.0

        # print the constants
        self._print_constants()

        # verify that the constants are the same as c
        self._verify_constants()

        # figure machine size needed at a min
        min_chips = (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC) / 16

        # set up the front end and ask for the detected machines dimensions
        front_end.setup(
            machine_time_step=machine_time_step,
            time_scale_factor=time_scale_factor,
            n_chips_required=min_chips)

        # contain the vertices for the connection aspect
        self._vertices = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

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

        # build vertices
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                psi = self._psi[x][y]
                p = self._pressure_calculation(x, y)
                u = self._mass_flux_u[x][y]
                v = self._mass_flux_v[x][y]

                vert = WeatherVertex(
                    p=p, u=u, v=v,
                    tdt=TDT, dx=DX, dy=DY, fsdx=FSDX, fsdy=FSDY,
                    alpha=ALPHA, label="weather_vertex{}:{}".format(x, y))

                logger.info(
                    "for vertex {}:{} p = {} u = {} v = {}".format(
                        x, y, p, u, v))

                self._vertices[x][y] = vert
                front_end.add_machine_vertex_instance(vert)

        # build edges
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._build_edges_for_vertex(x, y)

    @staticmethod
    def _print_constants():
        """ prints and checks constants from c and python

        :return: None
        """
        logger.info("constant DT    = {}".format(DT))
        logger.info("constant TDT   = {}".format(TDT))
        logger.info("constant DX    = {}".format(DX))
        logger.info("constant DY    = {}".format(DY))
        logger.info("constant FSDX  = {}".format(FSDX))
        logger.info("constant FSDY  = {}".format(FSDY))
        logger.info("constant A     = {}".format(A))
        logger.info("constant ALPHA = {}".format(ALPHA))
        logger.info("constant EL    = {}".format(EL))
        logger.info("constant PI    = {}".format(PI))
        logger.info("constant TPI   = {}".format(TPI))
        logger.info("constant DI    = {}".format(DI))
        logger.info("constant DJ    = {}".format(DJ))
        logger.info("constant PCF   = {}".format(PCF))

    def _verify_constants(self):
        if DT != 90.0:
            raise Exception("DT is wrong")
        if TDT != 90.0:
            raise Exception("TDT is wrong")
        if DX != 100000.0:
            raise Exception("DX is wrong")
        if DY != 100000.0:
            raise Exception("DY is wrong")
        if FSDX != 0.000040:
            raise Exception("FSDX is wrong")
        if FSDY != 0.000040:
            raise Exception("FSDY is wrong")
        if A != 1000000.0:
            raise Exception("A is wrong")
        if ALPHA != 0.001000:
            raise Exception("ALPHA is wrong")
        if EL != 300000.0:
            raise Exception("EL is wrong")
        if PI != 3.141593:
            raise Exception("PI is wrong")
        if TPI != 6.283185:
            raise Exception("TPI is wrong")
        if DI != 2.094395:
            raise Exception("DI is wrong")
        if DJ != 2.094395:
            raise Exception("DJ is wrong")
        if PCF != 109.662277:
            raise Exception("PCF is wrong")


    def _sort_out_psi(self):
        """ calculates the psi values for each atom

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._psi[x][y] = self._psi_calculation(x, y)

    def _sort_out_u(self):
        """calculates the u values for each atom

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._mass_flux_u[x][y] = \
                    self._mass_flux_u_calculation(x, y, self._psi)

    def _sort_out_v(self):
        """calculates the u values for each atom

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
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
            (x, (y + 1) % MAX_Y_SIZE_OF_FABRIC, "N"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
                (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NE"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC, y, "E"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
                (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SE"),
            (x, (y - 1) % MAX_Y_SIZE_OF_FABRIC, "S"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
                (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SW"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC, y, "W"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
                (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NW")]

        # build edges for each direction for this vertex
        for (dest_x, dest_y, compass) in positions:
            front_end.add_machine_edge_instance(WeatherDemoEdge(
                self._vertices[x][y], self._vertices[dest_x][dest_y],
                compass, "edge between {} and {}".format(
                    self._vertices[x][y], self._vertices[dest_x][dest_y])),
                "DATA")

    @staticmethod
    def _psi_calculation(x, y):
        """ creates the psi calculation

        :param x: the x coord of the vertex to make a psi of
        :param y: the y coord of the vertex to make a psi of
        :return: the psi calculation
        """
        return A * math.sin((x + 0.5) * DI) * math.sin((y + 0.5) * DJ)

    @staticmethod
    def _pressure_calculation(x, y):
        """ creates the p calculation

        :param x: the x coord of the vertex to make a p of
        :param y: the y coord of the vertex to make a p of
        :return: the p calculation
        """
        return PCF * (math.cos(2.0 * x * DI) +
                      math.cos(2.0 * y * DJ)) + 50000.0

    @staticmethod
    def _mass_flux_u_calculation(x, y, psi):
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
                 [(y % MAX_Y_SIZE_OF_FABRIC)]) / DY

    @staticmethod
    def _mass_flux_v_calculation(x, y, psi):
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
                [(y % MAX_Y_SIZE_OF_FABRIC)]) / DX

    def print_init_states(self):
        """ print to the logger data for verification

        :return: None
        """
        logger.info("Number of points in the x direction {}\n"
            .format(MAX_X_SIZE_OF_FABRIC))
        logger.info("Number of points in the y direction {}\n"
            .format(MAX_Y_SIZE_OF_FABRIC))
        logger.info("grid spacing in the x direction {}\n".format(DX))
        logger.info("grid spacing in the y direction {}\n".format(DY))
        logger.info("time step {}\n".format(DT))
        logger.info("time filter parameter {}\n".format(ALPHA))

        square_min = min(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)

        # print p elements from vertex
        logger.info("initial elements of p\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}p{}".format(
                    position_x, position_y,
                    self._vertices[position_x][position_y].p))

        # print u elements from vertex
        logger.info("initial elements of u\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}u{}".format(
                    position_x, position_y,
                    self._vertices[position_x][position_y].u))

        # print v elements from vertex
        logger.info("initial elements of v\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}v{}".format(
                    position_x, position_y,
                    self._vertices[position_x][position_y].v))

    @staticmethod
    def run(runtime):
        """ runs the network for a given simulation time in ms

        :param runtime: the runtime in ms
        :return: None
        """
        # run the simulation
        front_end.run(runtime)

    @staticmethod
    def print_diagonal_data(recorded_data):
        """ print the messages c code does at end

        :param recorded_data: the recorded data
        :return: None
        """

        # figure min diagnal for the prints
        square_min = min(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)

        # do the final prints as in c
        logger.info(" cycle number {} model time in hours {}\n".format(
            RUNTIME,  DT * RUNTIME))

        # print p elements from data
        logger.info("diagonal elements of p")
        for position in range(0, square_min):
            logger.info("{}".format(
                recorded_data[(position, position)]['p'][RUNTIME - 1]))

        # print u elements from data
        logger.info("diagonal elements of u")
        for position in range(0, square_min):
            logger.info("{}".format(
                recorded_data[(position, position)]['u'][RUNTIME - 1]))

        # print v elements from data
        logger.info("diagonal elements of v")
        for position in range(0, square_min):
            logger.info("{}".format(
                recorded_data[(position, position)]['v'][RUNTIME - 1]))

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

    @staticmethod
    def print_all_data(recorded_data):
        """ prints all data items extracted from the spinnaker machine.
        mainly used for debug proposes.

        :param recorded_data:
        the recorded data extracted from the spinnaker machine
        :return None
        """

        # print all elements for all times
        for time in range(0, 30):

            # print all for this time
            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} p is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['p'][time]))
                    logger.info("{}:{}:{} v is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['v'][time]))
                    logger.info("{}:{}:{} u is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['u'][time]))
                    logger.info("{}:{}:{} cu is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['cu'][time]))
                    logger.info("{}:{}:{} cv is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['cv'][time]))
                    logger.info("{}:{}:{} z is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['z'][time]))
                    logger.info("{}:{}:{} h is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['h'][time]))

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
    data = run.extract_data()
    # print data to screen
    run.print_all_data(data)
    run.print_diagonal_data(data)

    # finish sim on machine. basically clean up for future sims.
    run.stop()
