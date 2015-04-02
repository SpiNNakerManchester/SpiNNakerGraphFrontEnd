"""
DatabaseConnection connection to the graph front end database
"""
from spinnman.exceptions import SpinnmanIOException
from spinnman.constants import CONNECTION_TYPE
from spinnman.messages.eieio.command_messages.eieio_command_header \
    import EIEIOCommandHeader
from spinnman.data.little_endian_byte_array_byte_reader \
    import LittleEndianByteArrayByteReader
from spinnman.data.little_endian_byte_array_byte_writer \
    import LittleEndianByteArrayByteWriter
from spinnman.connections.abstract_classes.abstract_udp_connection \
    import AbstractUDPConnection


from spynnaker_graph_front_end.utilities.connections.database_reader \
    import DatabaseReader

from threading import Thread
import select
import socket
import traceback
import logging

logger = logging.getLogger(__name__)


class DatabaseConnection(AbstractUDPConnection, Thread):
    """ A connection from the sPyNNaker toolchain which will be notified\
        when the database has been written, and can then respond when the\
        database has been read, and further wait for notification that the\
        simulation has started.
    """

    def __init__(self, database_callback_function,
                 start_callback_function=None, local_host=None,
                 local_port=19999):
        """

        :param database_callback_function: A function to be called when the\
                    database message has been received.  This function should\
                    take a single parameter, which will be a DatabaseReader\
                    object.  Once the function returns, it will be assumed\
                    that the database has been read, and the return response\
                    will be sent.
        :type database_callback_function: function(\
                    :py:class:`spynnaker_external_devices.pyNN.connections.database_reader.DatabaseReader`)\
                    -> None
        :param start_callback_function: A function to be called when the start\
                    message has been received.  This function should not take\
                    any parameters or return anything.
        :type start_callback_function: function() -> None
        :param local_host: Optional specification of the local hostname or\
                    ip address of the interface to listen on
        :type local_host: str
        :param local_port: Optional specification of the local port to listen\
                    on.  Must match the port that the toolchain will send the\
                    notification on (19999 by default)
        :type local_port: int
        """
        AbstractUDPConnection.__init__(
            self, local_host=local_host, local_port=local_port,
            remote_host=None, remote_port=None)
        Thread.__init__(self)
        self._database_callback_function = database_callback_function
        self._start_callback_function = start_callback_function
        self.start()

    @property
    def connection_type(self):
        """

        :return:
        """
        return CONNECTION_TYPE.UDP_IPTAG

    def supports_sends_message(self, message):
        """

        :param message:
        :return:
        """
        return False

    def run(self):
        """

        :return:
        """
        try:
            logger.info(
                "Waiting for message to indicate that the database is ready")
            read_ready, _, _ = select.select([self._socket], [], [])
            if not read_ready:
                raise socket.timeout()
            raw_data, address = self._socket.recvfrom(512)

            # Read the read packet confirmation
            logger.info("Reading database")
            reader = LittleEndianByteArrayByteReader(bytearray(raw_data))
            EIEIOCommandHeader.read_eieio_header(reader)
            database_path = str(reader.read_bytes())

            # Call the callback
            self._database_callback_function(DatabaseReader(database_path))

            # Send the response
            logger.info(
                "Notifying the toolchain that the database has been read")
            writer = LittleEndianByteArrayByteWriter()
            EIEIOCommandHeader(1).write_eieio_header(writer)
            self._socket.sendto(writer.data, address)

            # Wait for the start of the simulation
            if self._start_callback_function is not None:
                logger.info(
                    "Waiting for message to indicate that the simulation has"
                    " started")
                read_ready, _, _ = select.select([self._socket], [], [])
                if not read_ready:
                    raise socket.timeout()
                raw_data, address = self._socket.recvfrom(512)

                # Call the callback
                self._start_callback_function()

        except Exception as e:
            traceback.print_exc()
            raise SpinnmanIOException(str(e))
