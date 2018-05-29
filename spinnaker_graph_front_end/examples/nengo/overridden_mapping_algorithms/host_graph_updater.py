import time

class HostGraphUpdator(object):

    SLEEP_PERIOD = 0.0001

    def __call__(self, host_graph, time_step):
        while run_time < exp_time:
            # Run a step
            host_graph.step()
            run_time = time.time() - start_time

            # If that step took less than timestep then spin
            time.sleep(0.0001)
            while run_time < host_steps * local_timestep:
                time.sleep(0.0001)
                run_time = time.time() - start_time
        finally:
        # Stop the IO thread whatever occurs
        io_thread.stop()