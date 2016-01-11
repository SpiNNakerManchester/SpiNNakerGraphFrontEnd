from spinnman.connections.udp_packet_connections.udp_connection \
    import UDPConnection

import logging

from spinnman.transceiver import create_transceiver_from_hostname
from spinnman.model.core_subset import CoreSubset
import time
from spinnman.exceptions import SpinnmanTimeoutException
from result import SelectResult
from result import Result
from result import Entry

import socket_translator

logger = logging.getLogger(__name__)

class SpiDBSocketConnection(UDPConnection):

    def __init__(self):
        UDPConnection.__init__(self)

        self.ip_address = "192.168.240.253" #todo should not be hardcoded
        self.port = 11111                   #todo should not be hardcoded

        self.transceiver = create_transceiver_from_hostname(self.ip_address, 3)

    def run(self, sqlQueries):
        queryIds = list() # useful if instead of using incrementing ids
                          # we use hash values for each query or such
        i = 0
        for q in sqlQueries:
            self.sendQuery(i,q)
            queryIds.append(i)
            i += 1
            #time.sleep(0.1) #todo hmmm....

        return self.receive_all(queryIds)

    def sendQuery(self, i, q):
        queryStructs = socket_translator.generateQueryStructs(i,q)
        for s in queryStructs:
            self.send_to(s, (self.ip_address, self.port))

    def recv(self):
        return self.receive()

    def receive_all(self, queryIds):
        id_to_index = {}

        for i in range(len(queryIds)):
            id_to_index[queryIds[i]] = i

        results = [None] * len(queryIds)

        time_sent = time.time() * 1000

        responseBuffer = []

        while True:
            try:
                s = self.receive(0.5) #todo lower that...
                print s

                responseBuffer.append((time.time() * 1000 - time_sent,
                                  s))

            except SpinnmanTimeoutException as e:
                print e
                break

        for t, s in responseBuffer:
            response = socket_translator.translateResponse(s)
            response.response_time = t

            i = id_to_index[response.id]
            if results[i] is None:
                if response.cmd == "SELECT":
                    results[i] = SelectResult()
                else:
                    results[i] = Result()

            results[i].addResponse(response)

        return results

    def iobuf(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(
                        core_subsets = [CoreSubset(x, y, [p])])
        return iobufs[0]