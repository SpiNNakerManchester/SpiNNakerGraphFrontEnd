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

        self.i=0

    def run(self, sqlQueries):
        j=self.i

        for q in sqlQueries:
            if len(q) is 0 or q.isspace():
                continue

            self.sendQuery(self.i,q)
            self.i+=1
            #time.sleep(0.1) #todo hmmm....

        return self.receive_all(j,self.i)

    def sendQuery(self, i, q):
        queryStructs = socket_translator.generateQueryStructs(i,q)
        for s in queryStructs:
            self.send_to(s, (self.ip_address, self.port))

    def recv(self):
        return self.receive()

    def receive_all(self, n,m):
        results = [None] * (m-n)

        time_sent = time.time() * 1000

        responseBuffer = []

        while True:
            try:
                s = self.receive(0.5)
                time_now = time.time() * 1000

                responseBuffer.append((time_now - time_sent,s))
                #print s

            except SpinnmanTimeoutException as e:
                break

        for t, s in responseBuffer:
            response = socket_translator.translateResponse(s)
            response.response_time = t
            print ">>> {}".format(response)

            if results[response.id-n] is None:
                if response.cmd == "SELECT":
                    results[response.id-n] = SelectResult()
                else:
                    results[response.id-n] = Result()

            results[response.id-n].addResponse(response)

        return results

    def iobuf(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(
                        core_subsets = [CoreSubset(x, y, [p])])
        return iobufs[0]