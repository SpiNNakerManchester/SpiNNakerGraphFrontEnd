import spinnaker_graph_front_end as sim
from pacman.model.constraints.placer_constraints import ChipAndCoreConstraint
from spinn_front_end_common.utility_models import \
    DataSpeedUpPacketGatherMachineVertex
from spinnaker_graph_front_end.examples import \
    test_data_in_speed_up_test_multi_board_run
from spinnaker_graph_front_end.examples.\
    test_data_in_speed_up_test_multi_board_run.\
    large_dsg_data_vertex import LargeDSGDataVertex
from spinn_front_end_common.utilities import globals_variables
import os


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs):

        # setup system
        sim.setup(
            model_binary_module=test_data_in_speed_up_test_multi_board_run,
            n_chips_required=int(48 * 2.5))

        machine = sim.machine()
        for ethernet_chip in machine.ethernet_connected_chips:
            chips_on_board = list(machine.get_chips_on_board(ethernet_chip))

            chip_x, chip_y = chips_on_board[(len(chips_on_board) // 2)]

            # build verts
            reader = LargeDSGDataVertex(mbs * 1024 * 1024)
            reader.add_constraint(ChipAndCoreConstraint(x=chip_x, y=chip_y))

            # add verts to graph
            sim.add_machine_vertex_instance(reader)

        sim.run(5)

        # get data
        machine_graph = globals_variables.get_simulator()._mapping_outputs[
            "MemoryMachineGraph"]
        lpgmv = None
        for vertex in machine_graph.vertices:
            if isinstance(vertex, DataSpeedUpPacketGatherMachineVertex):
                lpgmv = vertex

        speed = None
        missing_seq = None
        with open(lpgmv._data_in_report_path, "r") as reader:
            lines = reader.readlines()
            for line in lines[2:-1]:
                bits = line.split("\t\t")
                if int(bits[3]) == mbs * 1024 * 1024:
                    print("for {} bytes, mbs is {} with missing seqs "
                          "of {}".format(mbs * 1024 * 1024, bits[5], bits[6]))
                    speed = bits[5]
                    missing_seq = bits[6]

        sim.stop()
        return speed, missing_seq


if __name__ == "__main__":

    # entry point for doing speed search
    data_sizes = [20]
    runner = Runner()

    data_times = dict()
    overall_data_times = list()
    failed_to_run_states = list()
    lost_data_pattern = dict()

    for mbs_to_run in data_sizes:
        print("###########################################"
              "###########################")
        print("running {}".format(mbs_to_run))
        print("##################################################"
              "####################")
        speed, missing_seq = runner.run(mbs_to_run)
        data_times[(mbs_to_run)] = (speed, missing_seq)

        writer_behaviour = "a"
        if not os.path.isfile("results"):
            writer_behaviour = "w"
        with open("results", writer_behaviour) as writer:
            writer.write(
                "running {}:{}:{}\n".format(mbs_to_run, speed, missing_seq))
    print(data_times)
