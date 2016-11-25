import logging
import random
import threading
import time

import examples.spiDB.python.python_common.socket_translator
from examples.spiDB.python.tests.result import InsertIntoResult
from examples.spiDB.python.tests.result import PutResult
from examples.spiDB.python.tests.result import Result
from examples.spiDB.python.tests.result import SelectResult

from spinn_front_end_common.utilities.database.database_connection import \
    DatabaseConnection

from spinnman.exceptions import SpinnmanTimeoutException
from spinnman.model.core_subset import CoreSubset

logger = logging.getLogger(__name__)


class SpiDBSocketConnection(DatabaseConnection):

    def __init__(self, local_port, start_callback=None):
        DatabaseConnection.__init__(
            self, start_callback_function=start_callback,
            local_port=local_port)
        self.add_database_callback(self._read_database_callback)

        self.i = 0

    def _read_database_callback(self, database_reader):
        self._ip_address, self._port = \
            database_reader.get_partitioned_live_input_details("root_0_0")
        logger.info("Connection ip address and port num are {}:{}".format(
            self._ip_address, self._port))

    def send_ping(self):
        i = random.randint(0, 100000)
        try:
            self.send_to(
                examples.spiDB.python.python_common.socket_translator.PING(i),
                (self._ip_address, self._port))
            time_sent = time.time()
            s = self.receive(0.01)
        except SpinnmanTimeoutException:
            return -1

        return (time.time()-time_sent)*1000

    def generate_all_queries(self, sqlQueries, type="SQL"):
        up_load_bytes = dict()
        packets_sent = 0
        queries = []

        for q in sqlQueries:
            if q is None or not q:
                continue

            query_structs = \
                examples.spiDB.python.python_common.\
                socket_translator.generateQueryStructs(self.i, q, type)

            queries.append((self.i,query_structs))

            bytes_in_query = 0

            for s in query_structs:
                bytes_in_query += len(s)

            up_load_bytes[self.i] = bytes_in_query
            packets_sent += len(query_structs)
            self.i += 1

        return {'queries': queries,
                'uploadBytes': up_load_bytes,
                'packetsSent': packets_sent}

    def send_query(self, i, q, type="SQL"):
        try:
            query_structs = examples.spiDB.python.python_common.\
                socket_translator.generateQueryStructs(i, q, type)
        except Exception as e:
            print e
            return 0

        bytes = 0

        for s in query_structs:
            bytes += len(s)
            self.send_to(s, (self._ip_address, self._port))

        return {'bytes': bytes, 'packets': len(query_structs)}

    def receive_all(
            self, sent_times, results, download_bytes, download_time_arr,
            last_received_arr, packets_received_arr):

        response_buffer = []

        while True:
            try:
                s = self.receive(1) #todo
                response_buffer.append((time.time(), s))
                #print s
            except SpinnmanTimeoutException:
                break

        if response_buffer:
            first_received = response_buffer[0][0]
            last_received = response_buffer[len(response_buffer)-1][0]
        else:
            first_received = 0
            last_received = 0

        download_time_arr[0] = last_received - first_received
        last_received_arr[0] = last_received

        try:
            for id, t in sent_times.iteritems():
                results[id] = Result()  # empty result
        except Exception as e:
            print e
            pass

        total = 0

        for t, s in response_buffer:
            response = examples.spiDB.python.python_common.\
                socket_translator.translateResponse(s)
            if response is None:
                continue

            total += len(s)
            packets_received_arr[0] += 1

            response.response_time = (t-sent_times[response.id]) * 1000

            r = results.get(response.id)
            if r is None or not r.responses:
                download_bytes[response.id] = 0
                if response.cmd == "SELECT":
                    results[response.id] = SelectResult()
                elif response.cmd == "INSERT_INTO":
                    results[response.id] = InsertIntoResult()
                elif response.cmd == "PUT":
                    results[response.id] = PutResult()
                else:
                    results[response.id] = Result()

            results[response.id].addResponse(response)
            download_bytes[response.id] += len(s)

        return results

    def execute(self, sql_queries, type="SQL"):
        sent_times = dict()

        results = dict()

        download_bytes = dict()

        download_time_arr = [0]
        last_received_arr = [0]

        packets_received_arr = [0]

        allQ = self.generate_all_queries(sql_queries, type)
        packets_sent = allQ['packetsSent']
        upload_bytes = allQ['uploadBytes']
        queries = allQ['queries']

        t = threading.Thread(target=self.receive_all,
                             args=(sent_times, results,
                                   download_bytes, download_time_arr,
                                   last_received_arr,
                                   packets_received_arr))
        t.start()

        milliseconds_wait = 0.2
        sleep_time = milliseconds_wait / 1000
        first_time_sent = time.time()

        for i, queryStructs in queries:
            sent_times[i] = time.time()
            for s in queryStructs:
                time.sleep(sleep_time)
                self.send_to(s, (self._ip_address, self._port))

        last_time_sent = time.time()-sleep_time

        t.join()

        return {'results': list(results.values()),
                'upload': sorted(upload_bytes.iteritems()),
                'download': sorted(download_bytes.iteritems()),
                'packetsSent': packets_sent,
                'packetsReceived': packets_received_arr[0],
                'uploadTimeSec': last_time_sent-first_time_sent,
                'downloadTimeSec': download_time_arr[0],
                'totalTimeSec': last_received_arr[0]-first_time_sent}

    def iobuf(self, x, y, p):
        iobufs = self.transceiver.get_iobuf(
                        core_subsets = [CoreSubset(x, y, [p])])
        return iobufs[0]