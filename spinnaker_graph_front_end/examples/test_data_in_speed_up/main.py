import spinnaker_graph_front_end as sim
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinnaker_graph_front_end.examples import test_data_in_speed_up
from spinnaker_graph_front_end.examples.test_data_in_speed_up.\
    large_dsg_data_vertex import LargeDSGDataVertex
import time

class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs, x, y):

        # setup system
        sim.setup(model_binary_module=test_data_in_speed_up,
                  n_chips_required=2)

        # build verts
        reader = LargeDSGDataVertex(mbs * 1024 * 1024)
        reader.add_constraint(ChipAndCoreConstraint(x=x, y=y))

        # add verts to graph
        sim.add_machine_vertex_instance(reader)

        start = float(time.time())
        sim.run(5)
        end = float(time.time())
        seconds = float(end - start)
        speed = (mbs * 8) / seconds
        print ("Read {} MB in {} seconds ({} Mb/s)".format(
            mbs, seconds, speed))
        sim.stop()

if __name__ == "__main__":

    # entry point for doing speed search
    # data_sizes = [1, 2, 5, 10, 20, 30, 50]
    data_sizes = [1, 2, 5, 10, 20, 30, 50, 100]
    locations = [(0, 0), (1, 1), (0, 3), (2, 4), (4, 0), (7, 7)]
    iterations_per_type = 100
    runner = Runner()

    data_times = dict()
    overall_data_times = list()
    failed_to_run_states = list()
    lost_data_pattern = dict()

    for mbs_to_run in data_sizes:
        for x_coord, y_coord in locations:
            for iteration in range(0, iterations_per_type):
                print "###########################################" \
                      "###########################"
                print "running {}:{}:{}:{}".format(
                    mbs_to_run, x_coord, y_coord, iteration)
                print "##################################################" \
                      "####################"
                runner.run(mbs_to_run, x_coord, y_coord)
