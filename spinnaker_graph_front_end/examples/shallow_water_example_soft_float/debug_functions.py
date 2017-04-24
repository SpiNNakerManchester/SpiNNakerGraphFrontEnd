import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class DebugCalls(object):

    def __init__(self):
        pass

    @staticmethod
    def print_constants(DT, TDT, DX, DY, FSDX, FSDY, A, ALPHA, EL, PI, TPI,
                         DI, DJ, PCF):
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
        logger.info("constant PI    = {:20.16f}".format(PI))
        logger.info("constant TPI   = {}".format(TPI))
        logger.info("constant DI    = {}".format(DI))
        logger.info("constant DJ    = {}".format(DJ))
        logger.info("constant PCF   = {}".format(PCF))

    @staticmethod
    def print_initial_values(
            MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC, psi):
        logger.info("printing init values of psi")
        for x in range(0, MAX_X_SIZE_OF_FABRIC):
            for y in range(0, MAX_Y_SIZE_OF_FABRIC):
                logger.info("psi for {}:{} is {}".format(
                    x, y, psi[x][y]))

    @staticmethod
    def read_in_p_from_file(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC):
        read_in_data = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

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
    def read_in_psi_from_file(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC):
        read_in_data = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

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
    def read_in_u_from_file(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC):
        read_in_data = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

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
    def read_in_v_from_file(MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC):
        read_in_data = [
            [None for _ in range(MAX_X_SIZE_OF_FABRIC)]
            for _ in range(MAX_Y_SIZE_OF_FABRIC)]

        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.join(dir_path, "initial_v.txt")
        reader = open(dir_path)

        for line in reader:
            bits = line.split(",")
            final_number_bits = bits[2].split("\n")
            read_in_data[int(bits[0])][int(bits[1])] = \
                float(final_number_bits[0])
        return read_in_data

    def print_init_states(self, MAX_X_SIZE_OF_FABRIC, MAX_Y_SIZE_OF_FABRIC,
                          DX, DY, DT, ALPHA, vertices):
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
            recorded_data, RUNTIME, MAX_X_SIZE_OF_FABRIC,
            MAX_Y_SIZE_OF_FABRIC):
        """ prints all data items extracted from the spinnaker machine.
        mainly used for debug proposes.

        :param recorded_data:
        the recorded data extracted from the spinnaker machine
        :return None
        """

        # print all elements for all times
        for time in range(0, RUNTIME):

            # print all for this time
            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} p is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['p'][time]))

            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} u is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['u'][time]))

            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} v is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['v'][time]))

            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} cu is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['cu'][time]))

            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} cv is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['cv'][time]))

            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} h is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['h'][time]))

            for x_coord in range(0, MAX_X_SIZE_OF_FABRIC):
                for y_coord in range(0, MAX_Y_SIZE_OF_FABRIC):
                    logger.info("{}:{}:{} z is {}".format(
                        x_coord, y_coord, time,
                        recorded_data[(x_coord, y_coord)]['z'][time]))