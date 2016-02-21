from spinnman.connections.udp_packet_connections.udp_connection \
    import UDPConnection

import logging

from spinnman.transceiver import create_transceiver_from_hostname
from spinnman.model.core_subset import CoreSubset
import time
from spinnman.exceptions import SpinnmanTimeoutException
from result import SelectResult
from result import InsertIntoResult
from result import Result
import threading

import random

import socket_translator

logger = logging.getLogger(__name__)

class SpiDBSocketConnection(UDPConnection):

    def __init__(self):
        UDPConnection.__init__(self)

        self.ip_address = "192.168.240.253"
        self.port = 11111

        #self.transceiver = create_transceiver_from_hostname(self.ip_address, 3)

        self.i = 0

    def sendPing(self):
        i = random.randint(0, 100000)
        try:
            self.send_to(socket_translator.PING(i),
                         (self.ip_address, self.port))
            time_sent = time.time()
            s = self.receive(0.1)
        except SpinnmanTimeoutException:
            return -1

        return (time.time()-time_sent)*1000

    def sendQuery(self, i, q, type="SQL"):
        queryStructs = socket_translator.generateQueryStructs(i,q,type)

        for s in queryStructs:
            self.send_to(s, (self.ip_address, self.port))

    def receive_all(self, sent_times, results):
        responseBuffer = []

        while True:
            try:
                s = self.receive(0.3)
                responseBuffer.append((time.time(), s))
                print s
            except SpinnmanTimeoutException:
                break

        for t, s in responseBuffer:
            response = socket_translator.translateResponse(s)
            if response is None:
                continue

            response.response_time = (t-sent_times[response.id])*1000

            if results.get(response.id) is None:
                if response.cmd == "SELECT":
                    results[response.id] = SelectResult()
                elif response.cmd == "INSERT_INTO":
                    results[response.id] = InsertIntoResult()
                else:
                    results[response.id] = Result()

            results[response.id].addResponse(response)

        return results

    def run(self, sqlQueries, type="SQL"):
        sentTimes = dict()
        results = dict()

        t = threading.Thread(target=self.receive_all,
                             args=(sentTimes, results))
        t.start()

        for q in sqlQueries:
            if len(q) is 0 or q.isspace():
                continue

            time.sleep(0.1)
            self.sendQuery(self.i, q, type)
            sentTimes[self.i] = time.time()

            self.i += 1

        t.join()

        return list(results.values())

    def iobuf(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(
                        core_subsets = [CoreSubset(x, y, [p])])
        return iobufs[0]