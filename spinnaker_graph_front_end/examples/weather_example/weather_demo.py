import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end.examples.weather_example.weather_edge import \
    WeatherDemoEdge

from spinnaker_graph_front_end.examples.weather_example.weather_vertex \
    import WeatherVertex
from pacman.model.graphs.machine.impl.machine_edge import MachineEdge

import math
import logging

logger = logging.getLogger(__name__)

# grid size
MAX_X_SIZE_OF_FABRIC = 64
MAX_Y_SIZE_OF_FABRIC = 64

# runtime
RUNTIME = 4000

# random state variable inits
DT = 90.0
TDT = DT
DX = 100000.0
DY = 100000.0
FSDX = 4.0 / DX
FSDY = 4.0 / DY
A = 1000000.0
ALPHA = 0.001
EL = MAX_Y_SIZE_OF_FABRIC * DX
PI = 4.0 * math.atan(float(1.0))
print PI
TPI = PI + PI
DI = TPI / MAX_X_SIZE_OF_FABRIC
DJ = TPI / MAX_Y_SIZE_OF_FABRIC
PCF = PI * PI * A * A / (EL * EL)


class WeatherRun(object):
    """
    weather network holder. creates the network for SpiNNaker.
    """

    def __init__(self):
        machine_time_step = 1000
        time_scale_factor = 1.0

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

    def _sort_out_psi(self):
        """

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._psi[x][y] = self._psi_calculation(x, y)

    def _sort_out_u(self):
        """

        :return:
        """
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._mass_flux_u[x][y] = \
                    self._mass_flux_u_calculation(x, y, self._psi)

    def _sort_out_v(self):
        """

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

        logger.info("initial diagonal elements of p\n")
        for position in range(0, square_min):
            logger.info("{}".format(self._vertices[position][position].p))

        logger.info("initial diagonal elements of u\n")
        for position in range(0, square_min):
            logger.info("{}".format(self._vertices[position][position].u))

        logger.info("initial diagonal elements of v\n")
        for position in range(0, square_min):
            logger.info("{}".format(self._vertices[position][position].v))

    @staticmethod
    def run(runtime):
        """ runs the network for a given simulation time in ms

        :param runtime: the runtime in ms
        :return: None
        """
        # run the simulation
        front_end.run(runtime)

    def extract_data(self):
        """ extracts and

        :return: None
        """
        # get recorded data
        recorded_data = dict()
        square_min = min(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)

        # get the data per vertex
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                recorded_data[(x, y)] = self._vertices[x][y].get_data(
                    front_end.transceiver(),
                    front_end.placements().get_placement_of_vertex(
                        self._vertices[x][y]))
        logger.info(recorded_data)

        logger.info(" cycle number {} model time in hours {}\n".format(
            RUNTIME,  DT * RUNTIME))

        logger.info("diagonal elements of p")
        for position in range(0, square_min):
            logger.info("{}".format(recorded_data[(position, position)]['p']))

        logger.info("diagonal elements of u")
        for position in range(0, square_min):
            logger.info("{}".format(recorded_data[(position, position)]['u']))

        logger.info("diagonal elements of v")
        for position in range(0, square_min):
            logger.info("{}".format(recorded_data[(position, position)]['v']))

    @staticmethod
    def stop():
        # clear the machine
        front_end.stop()

if __name__ == "__main__":
    """
    main entrance method
    """
    run = WeatherRun()
    run.print_init_states()
    #run.run(RUNTIME)
    run.run(1)
    run.extract_data()
    run.stop()
