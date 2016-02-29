from spinnman.connections.udp_packet_connections.udp_connection \
    import UDPConnection

import logging

from spinnman.transceiver import create_transceiver_from_hostname
from spinnman.model.core_subset import CoreSubset
import time
from spinnman.exceptions import SpinnmanTimeoutException
from result import PutResult
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
            s = self.receive(0.01)
        except SpinnmanTimeoutException:
            return -1

        return (time.time()-time_sent)*1000

    def sendQuery(self, i, q, type="SQL"):
        try:
            queryStructs = socket_translator.generateQueryStructs(i,q,type)
        except Exception as e:
            print e
            return 0

        bytes = 0

        for s in queryStructs:
            bytes += len(s)
            self.send_to(s, (self.ip_address, self.port))

        return {'bytes': bytes, 'packets': len(queryStructs)}

    def receive_all(self, sent_times, results,
                    downloadBytes, downloadTimeArr, packetsReceivedArr):

        responseBuffer = []

        firstReceived = time.time()

        while True:
            try:
                s = self.receive(1.5) #todo
                responseBuffer.append((time.time(), s))
                #print s
            except SpinnmanTimeoutException:
                break

        lastReceived = time.time() #todo

        for id, t in sent_times.iteritems():
            results[id] = Result() #empty result

        total = 0

        for t, s in responseBuffer:
            response = socket_translator.translateResponse(s)
            if response is None:
                continue

            total += len(s)
            packetsReceivedArr[0] += 1

            response.response_time = (t-sent_times[response.id]) * 1000

            r = results.get(response.id)
            if r is None or not r.responses:
                downloadBytes[response.id] = 0
                if response.cmd == "SELECT":
                    results[response.id] = SelectResult()
                elif response.cmd == "INSERT_INTO":
                    results[response.id] = InsertIntoResult()
                elif response.cmd == "PUT":
                    results[response.id] = PutResult()
                else:
                    results[response.id] = Result()

            results[response.id].addResponse(response)
            downloadBytes[response.id] += len(s)
            downloadTimeArr[0] = (lastReceived-firstReceived)*1000


        return results

    def run(self, sqlQueries, type="SQL"):
        sentTimes = dict()

        results = dict()

        uploadBytes = dict()
        downloadBytes = dict()

        downloadTimeArr = [1]

        packetsSent = 0
        packetsReceivedArr = [1]

        t = threading.Thread(target=self.receive_all,
                             args=(sentTimes, results,
                                   downloadBytes, downloadTimeArr,
                                   packetsReceivedArr))
        t.start()

        firstTimeSent = time.time()

        for q in sqlQueries:
            if len(q) is 0 or q.isspace():
                continue

            time.sleep(0.00008)
            #time.sleep(0.0005)
            sq = self.sendQuery(self.i, q, type)
            uploadBytes[self.i] = sq['bytes']
            packetsSent += sq['packets']
            sentTimes[self.i] = time.time()

            self.i += 1

        lastTimeSent = time.time()

        t.join()

        return {'results': list(results.values()),
                'upload': sorted(uploadBytes.iteritems()),
                'download': sorted(downloadBytes.iteritems()),
                'packetsSent': packetsSent,
                'packetsReceived': packetsReceivedArr[0],
                'uploadTime': (lastTimeSent-firstTimeSent)*1000,
                'downloadTime': downloadTimeArr[0]}

    def iobuf(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(
                        core_subsets = [CoreSubset(x, y, [p])])
        return iobufs[0]