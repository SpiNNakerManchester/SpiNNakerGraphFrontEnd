from spinnman.transceiver import create_transceiver_from_hostname
from spinnman.processes import AbstractMultiConnectionProcess
from spinnman.messages.scp.abstract_messages import AbstractSCPRequest
from spinnman.messages.sdp import SDPHeader, SDPFlag
from spinnman.messages.scp.enums.scp_command import SCPCommand
from spinnman.messages.scp.impl import CheckOKResponse
from spinnman.messages.scp import SCPRequestHeader
from spinnman.connections.udp_packet_connections import UDPConnection
from spinnman.constants import BIG_DATA_SCAMP_PORT, BIG_DATA_MAX_DATA_BYTES
from spinn_machine.core_subsets import CoreSubsets
from spinn_machine.core_subset import CoreSubset
from spinn_utilities.progress_bar import ProgressBar
from spalloc.job import Job
from time import sleep, time
from threading import Thread
import logging
import numpy
import traceback


class TestMessage(AbstractSCPRequest):

    def __init__(self, x, y, p, port):
        super(TestMessage, self).__init__(
            SDPHeader(flags=SDPFlag.REPLY_EXPECTED, tag=0,
                      destination_port=port, destination_cpu=p,
                      destination_chip_x=x, destination_chip_y=y),
            SCPRequestHeader(command=SCPCommand.CMD_VER, sequence=0))

    def get_scp_response(self):
        return CheckOKResponse("TEST", "TEST")


class TestProcess(AbstractMultiConnectionProcess):

    def __init__(self, txrx):
        super(TestProcess, self).__init__(txrx.scamp_connection_selector)
        self._recv_progress = None
        self.is_error = False

    def handle_response(self, response):
        self._recv_progress.update()

    def handle_error(self, request, exception, tb):
        self._recv_progress.update()
        traceback.print_exception(type(exception), exception, tb)
        self.is_error = True

    def test_send(self, targets, n_send):
        self._recv_progress = ProgressBar(n_send * len(targets),
                                          "Test Messages")
        for _ in range(n_send):
            for (x, y, p, port) in targets:
                self._send_request(TestMessage(x, y, p, port),
                                   callback=self.handle_response,
                                   error_callback=self.handle_error)
        self._finish()
        self._recv_progress.end()


recv_running = True


def recv_thread(conn, recv_data):
    global recv_running
    while recv_running:
        try:
            data = numpy.frombuffer(
                conn.receive(timeout=2.0, max_size=1600), dtype="uint8")
            index = data[0:4].view("uint32")[0]
            recv_data[index] = data
        except Exception:
            traceback.print_exc()
            print("Error in reception, giving up")
            recv_running = False


def test_scp():
    logging.basicConfig(level=logging.INFO)

    spalloc_host = "spinnaker.cs.manchester.ac.uk"
    spalloc_user = "Jenkins"
    board_version = 5
    n_boards = 1

    job = Job(n_boards, hostname=spalloc_host, owner=spalloc_user)

    job.wait_until_ready()
    hostname = job.hostname
    txrx = create_transceiver_from_hostname(hostname, board_version)
    txrx.ensure_board_is_ready()
    sleep(0.5)

    app_id = 18
    machine = txrx.get_machine_details()
    core_subsets = CoreSubsets()
    for x, y in machine.chip_coordinates:
        chip = machine.get_chip_at(x, y)
        subset = CoreSubset(x, y, range(1, chip.n_processors))
        core_subsets.add_core_subset(subset)

    print("Executing application")
    txrx.execute_flood(core_subsets, "scp_test.aplx", app_id, is_filename=True)

    process = TestProcess(txrx)
    targets = [(cs.x, cs.y, p, 3)
               for cs in core_subsets for p in cs.processor_ids]
    start = time()
    process.test_send(targets, 1000)
    diff = time() - start
    print("Took {:.2f} seconds".format(diff))
    assert(not process.is_error)

    print("Setting up data")
    txrx.setup_big_data(0, 0, 1)

    conn = UDPConnection(remote_host=hostname, remote_port=BIG_DATA_SCAMP_PORT)
    input_data = list()
    recv_data = list()
    global recv_running
    recv_running = True

    t = Thread(target=recv_thread, args=[conn, recv_data])
    t.start()

    for i in range(1000):
        data = numpy.concatenate((
            numpy.array([i], dtype="uint32").view("uint8"),
            numpy.random.randint(
                0, 255, BIG_DATA_MAX_DATA_BYTES - 4).astype("uint8")))
        recv_data.append(None)
        input_data.append(data)
        conn.send(bytearray(data))

    print("Waiting for receive to finish")
    while recv_running:
        sleep(0.1)

    last_received = -1
    for i in range(len(input_data)):
        if recv_data[i] is not None:
            if last_received + 1 != i:
                print("Missing", last_received + 1, "to", i - 1)
            last_received = i
            print("Received", i)
            equal = numpy.array_equal(input_data[i], recv_data[i])
            if not equal:
                print(["{:04d}".format(d) for d in range(len(input_data[i]))])
                print(["{:04x}".format(d) for d in input_data[i]])
                print(["{:04x}".format(d) for d in recv_data[i]])
            assert(equal)
    if last_received + 1 != len(input_data):
        print("Missing", last_received + 1, "to", len(input_data) - 1)

    print(txrx.get_big_data_info(0, 0))

    print("Ending big data")
    txrx.end_big_data(0, 0)

    print("Getting iobuf")
    io_bufs = txrx.get_iobuf(core_subsets)
    for buf in io_bufs:
        print(buf)

    print("Killing application")
    txrx.stop_application(app_id)

    print(txrx.get_scamp_version())
    print(txrx.get_scamp_version(1, 1))
