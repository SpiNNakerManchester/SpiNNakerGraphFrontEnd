import spinnaker_graph_front_end as sim
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinn_front_end_common.utility_models import \
    DataSpeedUpPacketGatherMachineVertex
from spinnaker_graph_front_end.examples import \
    test_data_in_speed_up_on_every_chip_at_same_time
from spinnaker_graph_front_end.examples.\
    test_data_in_speed_up_on_every_chip_at_same_time.\
    large_dsg_data_vertex import LargeDSGDataVertex
from spinn_front_end_common.utilities import globals_variables
import os


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs):

        # setup system
        sim.setup(
            model_binary_module=(
                test_data_in_speed_up_on_every_chip_at_same_time),
            n_chips_required=2)

        # build verts
        machine = sim.machine()
        for chip in machine.chips:
            reader = LargeDSGDataVertex(mbs * 1024 * 1024)
            reader.add_constraint(ChipAndCoreConstraint(x=chip.x, y=chip.y))

            # add vertice to graph
            sim.add_machine_vertex_instance(reader)

        sim.run(5000)
        machine_graph = globals_variables.get_simulator()._mapping_outputs[
            "MemoryMachineGraph"]

        lpgmv = None
        for vertex in machine_graph.vertices:
            if isinstance(vertex, DataSpeedUpPacketGatherMachineVertex):
                lpgmv = vertex

        data = dict()

        with open(lpgmv._data_in_report_path, "r") as reader:
            lines = reader.readlines()
            for line in lines[2:-1]:
                bits = line.split("\t\t")
                if int(bits[3]) == mbs * 1024 * 1024:
                    print "for {} bytes, mbs is {} with missing seqs " \
                          "of {}".format(mbs * 1024 * 1024, bits[5], bits[6])
                    data[(bits[0], bits[1])] = (bits[5], bits[6])

        sim.stop()
        return data


if __name__ == "__main__":

    # entry point for doing speed search
    data_sizes = [100]
    iterations_per_type = 100
    runner = Runner()

    data_times = dict()
    overall_data_times = list()
    failed_to_run_states = list()
    lost_data_pattern = dict()

    for mbs_to_run in data_sizes:
        for iteration in range(0, iterations_per_type):
            print "###########################################" \
                  "###########################"
            print "running {}:{}".format(mbs_to_run, iteration)
            print "##################################################" \
                  "####################"
            data = runner.run(mbs_to_run)
            for (x, y) in data.keys():
                data_times[(x, y, mbs_to_run, iteration)] = data[(x, y)]

            writer_behaviour = "a"
            if not os.path.isfile("results"):
                writer_behaviour = "w"
            with open("results", writer_behaviour) as writer:
                writer.write("running iteration {}\n".format(iteration))
                for (x, y) in data.keys():
                    speed, missing_seq = data[(x, y)]
                    writer.write(
                        "     {}:{}:{}:{}:{}\n".format(
                            x, y, mbs_to_run, speed, missing_seq))
    print data_times
