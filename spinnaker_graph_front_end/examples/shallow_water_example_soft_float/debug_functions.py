import logging
import os
import subprocess
import struct

logger = logging.getLogger(__name__)


class DebugCalls(object):

    def __init__(self):
        pass

    def verify_graph_setup_properly(
            self, vertices, max_x_size_of_fabric, max_y_size_of_fabric):
        for x in range(0, max_x_size_of_fabric):
            for y in range(0, max_y_size_of_fabric):
                self._handle_vertex_check(vertices[x][y])

    @staticmethod
    def _handle_vertex_check(vertex):
        compass = [
            [True, "NW"], [True, "N"], [True, "NE"],
            [False, "print"], [True, "W"], [False, "self"],
            [True, "E"], [False, "print"], [True, "SW"],
            [True, "S"], [True, "SE"], [False, "print"]]
        output_string = ""
        for position in range(0, len(compass)):
            if compass[position][0]:
                other_vertex = vertex._location_vertices[compass[position][1]]
                output_string += "[{}:{}]".format(
                    other_vertex.x, other_vertex.y)
            elif compass[position][1] == "print":
                output_string += "\n                          "
            elif compass[position][1] == "self":
                output_string += "[{}:{}]".format(vertex.x, vertex.y)
        logging.info(output_string)
    
    @staticmethod
    def run_orginial_c_code(max_x_size_of_fabric, max_y_size_of_fabric):
        # run c code for data
        args = ["./PURE-C/test", str(max_x_size_of_fabric),
                str(max_y_size_of_fabric)]

        # run the external c code that can generate pure intiial values 
        # as needed (debug verification) 
        # Run the external command
        child = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)
        child.wait()

    @staticmethod
    def print_constants(dt, tdt, dx, dy, fsdx, fsdy, a, alpha, el, pi, tpi,
                         di, dj, pcf):
        """ prints and checks constants from c and python
    
        :return: None
        """
        logger.info("constant dt    = {}".format(dt))
        logger.info("constant tdt   = {}".format(tdt))
        logger.info("constant dx    = {}".format(dx))
        logger.info("constant dy    = {}".format(dy))
        logger.info("constant fsdx  = {}".format(fsdx))
        logger.info("constant fsdy  = {}".format(fsdy))
        logger.info("constant a     = {}".format(a))
        logger.info("constant alpha = {}".format(alpha))
        logger.info("constant el    = {}".format(el))
        logger.info("constant pi    = {:20.16f}".format(pi))
        logger.info("constant tpi   = {}".format(tpi))
        logger.info("constant di    = {}".format(di))
        logger.info("constant dj    = {}".format(dj))
        logger.info("constant pcf   = {}".format(pcf))

    @staticmethod
    def print_initial_values(
            max_x_size_of_fabric, max_y_size_of_fabric, psi):
        logger.info("printing init values of psi")
        for x in range(0, max_x_size_of_fabric):
            for y in range(0, max_y_size_of_fabric):
                logger.info("psi for {}:{} is {}".format(
                    x, y, psi[x][y]))

    @staticmethod
    def read_in_p_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        read_in_data = [
            [None for _ in range(max_x_size_of_fabric)]
            for _ in range(max_y_size_of_fabric)]

        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.join(dir_path, "initial_p.txt")
        reader = open(dir_path)
        for line in reader:
            bits = line.split(",")
            final_number_bits = bits[2].split("\n")
            read_in_data[int(bits[0])][int(bits[1])] = \
                float(final_number_bits[0])
        return read_in_data

    @staticmethod
    def read_in_psi_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        read_in_data = [
            [None for _ in range(max_x_size_of_fabric)]
            for _ in range(max_y_size_of_fabric)]

        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.join(dir_path, "initial_psi.txt")
        reader = open(dir_path)
        for line in reader:
            bits = line.split(",")
            final_number_bits = bits[2].split("\n")
            read_in_data[int(bits[0])][int(bits[1])] = \
                float(final_number_bits[0])
        return read_in_data

    @staticmethod
    def read_in_u_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        read_in_data = [
            [None for _ in range(max_x_size_of_fabric)]
            for _ in range(max_y_size_of_fabric)]

        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.join(dir_path, "initial_u.txt")
        reader = open(dir_path)

        for line in reader:
            bits = line.split(",")
            final_number_bits = bits[2].split("\n")
            read_in_data[int(bits[0])][int(bits[1])] = \
                float(final_number_bits[0])
        return read_in_data

    @staticmethod
    def read_in_v_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        read_in_data = [
            [None for _ in range(max_x_size_of_fabric)]
            for _ in range(max_y_size_of_fabric)]

        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.join(dir_path, "initial_v.txt")
        reader = open(dir_path)

        for line in reader:
            bits = line.split(",")
            final_number_bits = bits[2].split("\n")
            read_in_data[int(bits[0])][int(bits[1])] = \
                float(final_number_bits[0])
        return read_in_data

    @staticmethod
    def print_vertex_bits(max_x_size_of_fabric, max_y_size_of_fabric,
                          vertices):
        """
        
        :param vertex: 
        :return: 
        """

        for x_coord in range(0, max_x_size_of_fabric):
            for y_coord in range(0, max_y_size_of_fabric):
                vertex = vertices[x_coord][y_coord]
                byte_array = struct.pack("<f", vertex.p)
                p_data = struct.unpack("<I", byte_array)[0]

                byte_array = struct.pack("<f", vertex.u)
                u_data = struct.unpack("<I", byte_array)[0]

                byte_array = struct.pack("<f", vertex.v)
                v_data = struct.unpack("<I", byte_array)[0]

                logger.info(
                    "for vertex {}:{} p = 0x{:08x} \t\t v = 0x{:08x} \t\t "
                    "u = 0x{:08x}".format(
                        x_coord, y_coord, p_data, v_data, u_data))

    def print_init_states(self, max_x_size_of_fabric, max_y_size_of_fabric,
                          dx, dy, dt, alpha, vertices):
        """ print to the logger data for verification

        :return: None
        """
        logger.info("number of points in the x direction {}\n"
                    .format(max_x_size_of_fabric))
        logger.info("number of points in the y direction {}\n"
                    .format(max_y_size_of_fabric))
        logger.info("grid spacing in the x direction {}\n".format(dx))
        logger.info("grid spacing in the y direction {}\n".format(dy))
        logger.info("time step {}\n".format(dt))
        logger.info("time filter parameter {}\n".format(alpha))

        square_min = min(max_x_size_of_fabric, max_y_size_of_fabric)

        # print p elements from vertex
        logger.info("initial elements of p\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}p{}".format(
                    position_x, position_y,
                    vertices[position_x][position_y].p))

        # print u elements from vertex
        logger.info("initial elements of u\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}u{}".format(
                    position_x, position_y,
                    vertices[position_x][position_y].u))

        # print v elements from vertex
        logger.info("initial elements of v\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}v{}".format(
                    position_x, position_y,
                    vertices[position_x][position_y].v))

    @staticmethod
    def print_all_data(
            recorded_data, runtime, max_x_size_of_fabric,
            max_y_size_of_fabric):
        """ prints all data items extracted from the spinnaker machine.
        mainly used for debug proposes.

        :param recorded_data:
        the recorded data extracted from the spinnaker machine
        :return None
        """

        # print all elements for all times
        for time in range(0, runtime):

            # print all for this time
            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} p is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['p'][time]))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} u is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['u'][time]))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} v is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['v'][time]))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} cu is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['cu'][time]))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} cv is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['cv'][time]))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} h is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['h'][time]))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} z is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['z'][time]))

    @staticmethod
    def print_diagonal_data(
            recorded_data, max_x_size_of_fabric, max_y_size_of_fabric,
            runtime, dt):
        """ print the messages c code does at end

        :param recorded_data: the recorded data
        :return: none
        """

        # figure min diagnal for the prints
        square_min = min(max_x_size_of_fabric, max_y_size_of_fabric)

        # do the final prints as in c
        logger.info(" cycle number {} model time in hours {}\n".format(
            runtime, dt * runtime))

        # print p elements from data
        logger.info("diagonal elements of p")
        for position in range(0, square_min):
            logger.info("{}".format(
                recorded_data[(position, position)]['p'][runtime - 1]))

        # print u elements from data
        logger.info("diagonal elements of u")
        for position in range(0, square_min):
            logger.info("{}".format(
                recorded_data[(position, position)]['u'][runtime - 1]))

        # print v elements from data
        logger.info("diagonal elements of v")
        for position in range(0, square_min):
            logger.info("{}".format(
                recorded_data[(position, position)]['v'][runtime - 1]))