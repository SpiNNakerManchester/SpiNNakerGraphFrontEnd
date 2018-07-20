

class NengoSetUpLiveIO(object):

    def __call__(self, machine_graph):

        class EthernetThread(threading.Thread):
            """Thread which handles transmitting and receiving IO values."""

            def __init__(self, ethernet_handler):
                # Initialise the thread
                super(EthernetThread, self).__init__(name="EthernetIO")

                # Set up internal references
                self.halt = False
                self.handler = ethernet_handler
                self.in_sock = ethernet_handler.in_socket
                self.in_sock.settimeout(0.0001)

            def run(self):
                while not self.halt:
                    # Read as many packets from the socket as we can
                    while True:
                        try:
                            data = self.in_sock.recv(512)
                        except IOError:
                            break  # No more to read

                        # Unpack the data, and store it as the input for the
                        # appropriate Node.
                        packet = SCPPacket.from_bytestring(data)
                        values = tp.fix_to_np(
                            np.frombuffer(packet.data, dtype=np.int32)
                        )

                        # Get the Node
                        node = self.handler._node_incoming[(packet.src_x,
                                                            packet.src_y,
                                                            packet.src_cpu)]
                        with self.handler.node_input_lock:
                            self.handler.node_input[node] = values[:]

            def stop(self):
                """Stop the thread from running."""
                self.halt = True
                self.join()


