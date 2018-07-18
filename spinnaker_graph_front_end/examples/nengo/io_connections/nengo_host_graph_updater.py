import time
from threading import Condition


class NengoHostGraphUpdater(object):

    __slots__ = [
        #
        '_host_network',
        #
        '_time_step',
        #
        '_running',
        #
        '_running_condition'
    ]

    def __init__(self, host_network, time_step):
        self._host_network = host_network
        self._time_step = time_step
        self._running = False
        self._running_condition = Condition()

    def start_resume(self, label, connection):

        # set the fag to running
        self._running_condition.acquire()
        self._running = True
        self._running_condition.release()

        # check flag
        self._running_condition.acquire()
        while self._running:
            self._running_condition.release()

            # time holder
            start_time = time.time()

            # Run a step
            self._host_network.step()

            # hang till time step over
            run_time = time.time() - start_time

            # If that step took less than timestep then hang
            time.sleep(0.0001)
            while run_time < self._time_step:
                time.sleep(0.0001)
                run_time = time.time() - start_time

    def pause_stop(self, label, connection):
        self._running_condition.acquire()
        self._running = False
        self._running_condition.release()
