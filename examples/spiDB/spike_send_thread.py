from spinnman.exceptions import SpinnmanIOException
from spinnman.messages.eieio.command_messages.eieio_command_header \
    import EIEIOCommandHeader
from spinnman.connections.udp_packet_connections.udp_connection \
    import UDPConnection


from spinn_front_end_common.utilities.database.database_reader \
    import DatabaseReader

from spinnman.connections.udp_packet_connections.udp_eieio_connection \
    import UDPEIEIOConnection

from spinnman.messages.eieio.data_messages.eieio_32bit\
    .eieio_32bit_data_message import EIEIO32BitDataMessage

from threading import Thread
import traceback
import logging

import time
import struct

logger = logging.getLogger(__name__)


class SpikeSendThread(Thread):
    """ A connection from the toolchain which will be notified\
        when the database has been written, and can then respond when the\
        database has been read, and further wait for notification that the\
        simulation has started.
    """


    def __init__(self, local_port=19999):
        """

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

        self._sender_connection = UDPEIEIOConnection()

        self.conn = UDPConnection()

        Thread.__init__(self,
                        name="spynnaker database connection for {}"
                        .format(local_port))
        self.start()

    def run(self):
        try:
            time.sleep(10)
            print "SENDING EVEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEENT"

            ip_address = "192.168.240.253"
            port = 11111

                                            #put
            s = struct.pack("BBI128sBI128s", 0, 2, 10, "ABCDEFGHIJ", 2, 5, "World")

            self.conn.send_to(s, (ip_address, port))

            time.sleep(5)
                                            #pull
            s = struct.pack("BBI128sBI128s", 1, 2, 10, "ABCDEFGHIJ", 0, 0, "")

            self.conn.send_to(s, (ip_address, port))

        except Exception as e:
            traceback.print_exc()
            raise SpinnmanIOException(str(e))
