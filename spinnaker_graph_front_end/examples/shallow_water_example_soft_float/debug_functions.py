import logging
import os
import subprocess
import struct

import binascii

logger = logging.getLogger(__name__)


class DebugCalls(object):

    def __init__(self):
        pass

    @staticmethod
    def convert(data):
        """ converts between floats and ints for printing
        
        :param data: the float to convert into a int for printing in hex
        :return: the int for printing in hex
        """
        byte_array = struct.pack("<f", data)
        val = struct.unpack("<I", byte_array)[0]
        result = hex((val + (1 << 32)) % (1 << 32))
        return result



    def verify_graph_setup_properly(
            self, vertices, max_x_size_of_fabric, max_y_size_of_fabric):
        """  prints out the vertex neighbours for visual verification that the 
        graph has been built correctly
        
        :param vertices: the set of vertices
        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :return: None
        """
        for x in range(0, max_x_size_of_fabric):
            for y in range(0, max_y_size_of_fabric):
                self._handle_vertex_check(vertices[x][y])

    @staticmethod
    def _handle_vertex_check(vertex):
        """ prints the vertex neighbours for visual verification that the 
        graph has been built correctly
        
        :param vertex: the vertex to print the neighbours of
        :return: 
        """
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
        """ runs the original c code so that we can rectify the differences 
        between c and python code for float accuracy
        
        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :return: 
        """
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
        
        :param dt: ?????
        :param tdt: ?????
        :param dx: ????
        :param dy: ????
        :param fsdx: ????
        :param fsdy: ????
        :param a: ????
        :param alpha: ?????
        :param el: ?????
        :param pi: math pi
        :param tpi: ????
        :param di: ????
        :param dj: ????
        :param pcf: ????
        :return: 
        """
        logger.info("constant dt    = {}".format(DebugCalls.convert(dt)))
        logger.info("constant tdt   = {}".format(DebugCalls.convert(
            tdt)))
        logger.info("constant dx    = {}".format(DebugCalls.convert(dx)))
        logger.info("constant dy    = {}".format(DebugCalls.convert(dy)))
        logger.info("constant fsdx  = {}".format(DebugCalls.convert(
            fsdx)))
        logger.info("constant fsdy  = {}".format(DebugCalls.convert(
            fsdy)))
        logger.info("constant a     = {}".format(DebugCalls.convert(a)))
        logger.info("constant alpha = {}".format(DebugCalls.convert(
            alpha)))
        logger.info("constant el    = {}".format(DebugCalls.convert(el)))
        logger.info("constant pi    = {}".format(DebugCalls.convert(pi)))
        logger.info("constant tpi   = {}".format(DebugCalls.convert(
            tpi)))
        logger.info("constant di    = {}".format(DebugCalls.convert(di)))
        logger.info("constant dj    = {}".format(DebugCalls.convert(dj)))
        logger.info("constant pcf   = {}".format(DebugCalls.convert(
            pcf)))

    @staticmethod
    def print_initial_values(
            max_x_size_of_fabric, max_y_size_of_fabric, psi):
        """ prints out the initial psi values

        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :param psi: the psi values
        :return: 
        """
        logger.info("printing init values of psi")
        for x in range(0, max_x_size_of_fabric):
            for y in range(0, max_y_size_of_fabric):
                logger.info("psi for {}:{} is {}".format(
                    x, y, DebugCalls.convert(psi[x][y])))

    @staticmethod
    def read_in_p_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        """ read hard values from a file

        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :return: the p data as array of [x][y]
        """
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
        """ read hard values from a file

        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :return: the psi data as array of [x][y]
        """
        read_in_data = [
            [None for _ in range(max_x_size_of_fabric)]
            for _ in range(max_y_size_of_fabric)]

        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.join(dir_path, "initial_psi.txt")
        reader = open(dir_path)
        for line in reader:
            bits = line.split(",")
            final_number_bits = bits[2].split(" \n")
            read_in_data[int(bits[0])][int(bits[1])] = \
                float(final_number_bits[0])
        return read_in_data

    @staticmethod
    def read_in_u_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        """ read hard values from a file

        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :return: the u data as array of [x][y]
        """

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
    def periodic_continuation(
            max_y_size_of_fabric, max_x_size_of_fabric, vertices):
        """ does some boundary case switching

        :return: none
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

    @staticmethod
    def read_in_v_from_file(max_x_size_of_fabric, max_y_size_of_fabric):
        """ read hard values from a file
        
        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :return: the v data as array of [x][y]
        """
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
        :param max_y_size_of_fabric: the size of the grid in y axis
        :param max_x_size_of_fabric: the size of the grid in x axis
        :param vertices: the vertices of the simulation
        :return: 
        """

        for x_coord in range(0, max_x_size_of_fabric):
            for y_coord in range(0, max_y_size_of_fabric):
                vertex = vertices[x_coord][y_coord]

                logger.info(
                    "for vertex {}:{} p = {} \t\t v = {} \t\t "
                    "u = {}".format(
                        x_coord, y_coord, DebugCalls.convert(vertex.p),
                        DebugCalls.convert(vertex.v),
                        DebugCalls.convert(vertex.u)))

    @staticmethod
    def print_init_states(max_x_size_of_fabric, max_y_size_of_fabric,
                          dx, dy, dt, alpha, vertices):
        """ print to the logger data for verification
        :param max_x_size_of_fabric: size of grid in x axis
        :param max_y_size_of_fabric: size of grid in y axis
        :param dt: ????
        :param dx: ?????
        :param dy: ?????
        :param alpha: ?????
        :param vertices: the verts of the simulation
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
                logger.info("{}:{}p={}".format(
                    position_x, position_y,
                    DebugCalls.convert(vertices[position_x][position_y].p)))

        # print u elements from vertex
        logger.info("initial elements of u\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}u={}".format(
                    position_x, position_y,
                    DebugCalls.convert(vertices[position_x][position_y].u)))

        # print v elements from vertex
        logger.info("initial elements of v\n")
        for position_x in range(0, square_min):
            for position_y in range(0, square_min):
                logger.info("{}:{}v={}".format(
                    position_x, position_y,
                    DebugCalls.convert(vertices[position_x][position_y].v)))

    @staticmethod
    def print_all_data(
            recorded_data, runtime, max_x_size_of_fabric,
            max_y_size_of_fabric):
        """ prints all data items extracted from the spinnaker machine.
        mainly used for debug proposes.
        
        :param max_x_size_of_fabric: size of grid in x axis
        :param max_y_size_of_fabric: size of grid in y axis
        :param recorded_data:
        :param runtime: time to run in ms#
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
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['p'][time])))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} u is {}".format(
                        x_coord, y_coord, time,
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['u'][time])))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} v is {}".format(
                        x_coord, y_coord, time,
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['v'][time])))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} cu is {}".format(
                        x_coord, y_coord, time,
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['cu'][time])))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} cv is {}".format(
                        x_coord, y_coord, time,
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['cv'][time])))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} h is {}".format(
                        x_coord, y_coord, time,
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['h'][time])))

            for x_coord in range(0, max_x_size_of_fabric):
                for y_coord in range(0, max_y_size_of_fabric):
                    logger.info("{}:{}:{} z is {}".format(
                        x_coord, y_coord, time,
                        DebugCalls.convert(
                            recorded_data[(x_coord, y_coord)]['z'][time])))

    @staticmethod
    def print_diagonal_data(
            recorded_data, max_x_size_of_fabric, max_y_size_of_fabric,
            runtime, dt):
        """ print the messages c code does at end
        :param max_x_size_of_fabric: size of grid in x axis
        :param max_y_size_of_fabric: size of grid in y axis
        :param runtime: time to run in ms#
        :param dt: phft????
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
                DebugCalls.convert(
                    recorded_data[(position, position)]['p'][runtime - 1])))

        # print u elements from data
        logger.info("diagonal elements of u")
        for position in range(0, square_min):
            logger.info("{}".format(
                DebugCalls.convert(
                    recorded_data[(position, position)]['u'][runtime - 1])))

        # print v elements from data
        logger.info("diagonal elements of v")
        for position in range(0, square_min):
            logger.info("{}".format(
                DebugCalls.convert(
                    recorded_data[(position, position)]['v'][runtime - 1])))
