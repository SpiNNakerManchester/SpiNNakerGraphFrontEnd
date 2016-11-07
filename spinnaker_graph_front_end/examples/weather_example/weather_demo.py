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
        machine_time_step = 100
        time_scale_factor = 1.0

        # figure machine size needed at a min
        min_chips = (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC) / 16

        # set up the front end and ask for the detected machines dimensions
        front_end.setup(
            machine_time_step=machine_time_step,
            time_scale_factor=time_scale_factor,
            n_chips_required=min_chips)

        # figure out if machine can handle simulation
        #cores = front_end.get_number_of_cores_on_machine()
        #if cores <= (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC):
        #    raise KeyError("Don't have enough cores to run simulation")

        # contain the vertices for the connection aspect
        self._vertices = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

        # build vertices
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                psi = self._psi(x, y)
                p = self._p(x, y)
                u = self._u(x, y)
                v = self._v(x, y)

                hard_coded_east_u = None
                hard_coded_east_p = None
                hard_coded_east_v = None
                hard_coded_north_east_u = None
                hard_coded_north_east_p = None
                hard_coded_north_east_v = None
                hard_coded_north_u = None
                hard_coded_north_p = None
                hard_coded_north_v = None

                # if at east edge.
                if x == MAX_X_SIZE_OF_FABRIC - 1:
                    hard_coded_east_u = self._u(MAX_X_SIZE_OF_FABRIC, y)
                    hard_coded_east_p = self._p(MAX_X_SIZE_OF_FABRIC, y)
                    hard_coded_east_v = self._v(MAX_X_SIZE_OF_FABRIC, y)

                # if at north east edge.
                if (x == MAX_X_SIZE_OF_FABRIC - 1 and
                        y == MAX_Y_SIZE_OF_FABRIC - 1):
                    hard_coded_north_east_u = \
                        self._u(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)
                    hard_coded_north_east_p = \
                        self._p(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)
                    hard_coded_north_east_v = \
                        self._v(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC)

                # if at north edge
                if y == MAX_Y_SIZE_OF_FABRIC - 1:
                    hard_coded_north_u = self._u(x, MAX_Y_SIZE_OF_FABRIC)
                    hard_coded_north_p = self._p(x, MAX_Y_SIZE_OF_FABRIC)
                    hard_coded_north_v = self._v(x, MAX_Y_SIZE_OF_FABRIC)

                vert = WeatherVertex(
                    psi=psi, p=p, u=u, v=v,
                    at_edge_east=x == MAX_X_SIZE_OF_FABRIC - 1,
                    hard_coded_east_u=hard_coded_east_u,
                    hard_coded_east_p=hard_coded_east_p,
                    hard_coded_east_v=hard_coded_east_v,
                    at_edge_north_east=(
                        (x == MAX_X_SIZE_OF_FABRIC - 1) and
                        (y == MAX_Y_SIZE_OF_FABRIC - 1)),
                    hard_coded_north_east_u=hard_coded_north_east_u,
                    hard_coded_north_east_p=hard_coded_north_east_p,
                    hard_coded_north_east_v=hard_coded_north_east_v,
                    at_edge_north=y == MAX_Y_SIZE_OF_FABRIC - 1,
                    hard_coded_north_u=hard_coded_north_u,
                    hard_coded_north_p=hard_coded_north_p,
                    hard_coded_north_v=hard_coded_north_v,
                    tdt=TDT, dx=DX, dy=DY, fsdx=FSDX, fsdy=FSDY,
                    alpha=ALPHA, label="weather_vertex{}:{}".format(x, y))
                self._vertices[x][y] = vert
                front_end.add_machine_vertex_instance(vert)

        self._strange_movement_of_values()

        # build edges
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                self._build_edges_for_vertex(x, y)

    def _build_edges_for_vertex(self, x, y):
        """ for a given vertex, builds the edges that communicate
        different data types

        :param x: the vertex in x dimension
        :param y: the vertex in y dimension
        :return: None
        """
        positions = [
            (x, (y - 1), "S"),
            ((x - 1), (y - 1), "SW"),
            ((x - 1), y, "W")]
        for (dest_x, dest_y, compass) in positions:
            if (x < MAX_Y_SIZE_OF_FABRIC - 1 and
                    y < MAX_Y_SIZE_OF_FABRIC - 1):
                front_end.add_machine_edge_instance(WeatherDemoEdge(
                    self._vertices[x][y], self._vertices[dest_x][dest_y]),
                    "DATA")

    def _strange_movement_of_values(self):
        """ strange method that's moving values around in some diagonal form

        :return:  None
        """

        for position in range(0, MAX_X_SIZE_OF_FABRIC-1):
            self._vertices[0][position].u = \
                self._vertices[MAX_Y_SIZE_OF_FABRIC-1][position].u
            self._vertices[MAX_Y_SIZE_OF_FABRIC-1][position + 1].v = \
                self._vertices[0][position+1].v
        for position in range(0, MAX_Y_SIZE_OF_FABRIC-1):
            self._vertices[position][MAX_X_SIZE_OF_FABRIC-1].u = \
                self._vertices[position + 1][0].u
            self._vertices[position][0].v = \
                self._vertices[position][MAX_X_SIZE_OF_FABRIC-1].v
        self._vertices[0][MAX_X_SIZE_OF_FABRIC-1].u = \
            self._vertices[MAX_Y_SIZE_OF_FABRIC-1][0].u
        self._vertices[MAX_Y_SIZE_OF_FABRIC-1][0].v = \
            self._vertices[0][MAX_X_SIZE_OF_FABRIC-1].v

    @staticmethod
    def _psi(x, y):
        """ creates the psi calculation

        :param x: the x coord of the vertex to make a psi of
        :param y: the y coord of the vertex to make a psi of
        :return: the psi calculation
        """
        return A * math.sin((x + 0.5) * DI) * math.sin((y + 0.5) * DJ)

    @staticmethod
    def _p(x, y):
        """ creates the p calculation

        :param x: the x coord of the vertex to make a p of
        :param y: the y coord of the vertex to make a p of
        :return: the p calculation
        """
        return PCF * (math.cos(2.0 * x * DI) + math.cos(2.0 * y * DJ)) \
            + 50000.0

    def _u(self, x, y):
        """ creates the u calculation

        :param x: the x coord of the vertex to make a u of
        :param y: the y coord of the vertex to make a u of
        :return: the u calculation
        """
        return -(self._psi(x + 1, y + 1) - self._psi(x + 1, y)) / DY

    def _v(self, x, y):
        """ creates the v calculation

        :param x: the x coord of the vertex to make a v of
        :param y: the y coord of the vertex to make a v of
        :return: the v calculation
        """
        return (self._psi(x + 1, y + 1) - self._psi(x, y + 1)) / DX

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
    run.run(RUNTIME)
    run.extract_data()
    run.stop()
