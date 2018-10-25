import struct
import time
import spinnaker_graph_front_end as sim
from data_specification.utility_calls import get_region_base_address_offset
from spinnaker_graph_front_end.examples import \
    test_extra_monitor_core_data_extraction
from spinnaker_graph_front_end.examples.\
    test_extra_monitor_core_data_extraction.sdram_writer import SDRAMWriter

#import matplotlib.pyplot as plt
import psutil
import numpy as np

#import threading
#from logging import thread
from multiprocessing import Process
import subprocess
from pacman.model.constraints.placer_constraints.chip_and_core_constraint import ChipAndCoreConstraint


class Runner(object):

    def __init__(self):
        pass

    def run(self, mbs, nthreads):

        processes = []

        # setup system
        sim.setup(model_binary_module=test_extra_monitor_core_data_extraction,
                  n_chips_required=(650))

        machine = sim.machine()
        writers = list()
        ip_list = list()
        ethchip_list = list()

        for ethernet_chip in machine.ethernet_connected_chips:

            if str(ethernet_chip.ip_address) != "10.11.224.1":
                ip_list.append(ethernet_chip.ip_address)
                ethchip_list.append(ethernet_chip)

                if len(writers) < nthreads:
                    # build verts
                    writer = SDRAMWriter(mbs)

                    #Verify if desired chip exists, if not find an existing one different from the monitor one and use that one
                    if machine.is_chip_at(x=ethernet_chip.x + 3, y=ethernet_chip.y + 3):
                        writer.add_constraint(ChipAndCoreConstraint(x=ethernet_chip.x+3, y=ethernet_chip.y+3))
                    else:
                        for chip in machine.get_chips_on_board(ethernet_chip):
                            if chip != (ethernet_chip.x, ethernet_chip.y):
                                writer.add_constraint(ChipAndCoreConstraint(x=chip[0], y=chip[1]))
                                break

                    writers.append(writer)

                # add verts to graph
                sim.add_machine_vertex_instance(writer)

        sim.run(12)

        # get placements for extraction
        placements = sim.placements()
        #machine = sim.machine()

        writer_nearest_ethernet = list()
        writer_placements = list()

        for w in writers:
            writer_placement = placements.get_placement_of_vertex(w)
            writer_placements.append(writer_placement)
            writer_chip = \
                machine.get_chip_at(writer_placement.x, writer_placement.y)

            writer_nearest_ethernet.append(machine.get_chip_at(
                writer_chip.nearest_ethernet_x, writer_chip.nearest_ethernet_y))

        extra_monitor_vertices = sim.globals_variables.\
            get_simulator()._last_run_outputs['MemoryExtraMonitorVertices']
        extra_monitor_gatherers = sim.globals_variables.\
            get_simulator()._last_run_outputs[
                'MemoryMCGatherVertexToEthernetConnectedChipMapping']

        gatherers = list()
        receivers = list()

        for i in range(len(writer_nearest_ethernet)):
            gatherers.append(extra_monitor_gatherers[(writer_nearest_ethernet[i].x, writer_nearest_ethernet[i].y)])

            for vertex in extra_monitor_vertices:
                placement = placements.get_placement_of_vertex(vertex)
                if (placement.x == writer_placements[i].x and
                        placement.y == writer_placements[i].y):
                    receivers.append(vertex)

        cpu = psutil.cpu_percent(percpu=True)

        #=======================================================================
        # for i in range(nthreads):
        #     p = Process(target=gatherers[i].get_data, args=(ip_list[i], placements.get_placement_of_vertex(receivers[i]),
        #     self._get_data_region_address(sim.transceiver(), writer_placement),
        #     writer.mbs_in_bytes, ethchip_list[i].x, ethchip_list[i].y,))
        #     processes.append(p)
        #     print "process created"
        #=======================================================================

        for gatherer in gatherers:

            gatherer.set_cores_for_data_extraction(
                sim.transceiver(), extra_monitor_vertices, placements)

#===============================================================================
#         for i in processes:
#             i.start()
#
#         for i in processes:
#             i.join()
#===============================================================================

        plist = []

        regions = []

        for i in range(nthreads):
            regions.append(self._get_data_region_address(sim.transceiver(), writer_placements[i]))

        start = float(time.time())

        for i in range(nthreads):

            plist.append(subprocess.Popen(["./host_data_receiver",
                                           str(ip_list[i]),
                                           str(gatherers[i].get_port()),
                                           str(placements.get_placement_of_vertex(receivers[i]).x),
                                           str(placements.get_placement_of_vertex(receivers[i]).y),
                                           str(placements.get_placement_of_vertex(receivers[i]).p),
                                           "./read_"+str(i)+".txt",
                                           "./results/missing_"+str(mbs)+"mb_"+str(nthreads)+"threads_"+str(i+1)+".txt",
                                           str(writer.mbs_in_bytes),
                                           str(regions[i]),
                                           str(ethchip_list[i].x),
                                           str(ethchip_list[i].y),
                                           str(gatherers[i].get_chip_p()),
                                           str(gatherers[i].get_iptag()),
                                           str(gatherers[i].get_window_size()),
                                           str(gatherers[i].get_sliding_window())]))

        for i in plist:
            ret = i.wait()

        end = float(time.time())

        for gatherer in gatherers:
            gatherer.unset_cores_for_data_extraction(
                sim.transceiver(), extra_monitor_vertices, placements)


        #cpu % since last call
        cpu = psutil.cpu_percent(percpu=True)

        speed = (mbs * 8 * nthreads) / (end - start)
        timing = end - start

        #print "time taken to extract {} MB is {}. MBS of {}".format(
        #mbs, end - start, (mbs * 8) / (end - start))

        #self._check_data(data)
        sim.stop()

        return speed, timing, cpu

    @staticmethod
    def _get_data_region_address(transceiver, placement):
        # Get the App Data for the core
        app_data_base_address = transceiver.get_cpu_information_from_core(
            placement.x, placement.y, placement.p).user[0]

        # Get the provenance region base address
        base_address_offset = get_region_base_address_offset(
            app_data_base_address, SDRAMWriter.DATA_REGIONS.DATA.value)
        base_address_buffer = buffer(transceiver.read_memory(
            placement.x, placement.y, base_address_offset, 4))
        _ONE_WORD = struct.Struct("<I")
        return _ONE_WORD.unpack(str(base_address_buffer))[0]

    @staticmethod
    def _check_data(data):
        # check data is correct here
        elements = len(data) / 4
        ints = struct.unpack("<{}I".format(elements), data)
        start_value = 0
        for value in ints:
            if value != start_value:
                print "should be getting {}, but got {}".format(
                    start_value, value)
                start_value = value + 1
            else:
                start_value += 1


if __name__ == "__main__":

    timing = dict()
    runner = Runner()
    n = 30
    n_threads = 10
    nrep = 20
    errslist = list()

    speed = [[0 for i in range(nrep)] for elem in range(n_threads)]
    sumspeed = [0 for i in range(nrep)]

    spfile = bytearray((n-1)*n_threads)
    offset = 0
    offsetcpu = 0
    cpu_tmp = list()

    p = subprocess.call(["mkdir",
                         "results"])
    quantities = [1, 2, 5, 10, 30, 35, 40, 45, 50]

    for i in quantities:
        for l in range(3, n_threads+1):
	    rep = 1
	    sumproclist = list()
	    while rep <= nrep:
	    	rep += 1
            	print "mbs " + str(i) + " number of threads: " + str(l) + " rep " + str(rep-1)
		finished = False
		while not finished:
            		sp, tim, proc = runner.run(mbs=i, nthreads=l)
            		print "\n\n\n"+str(sp)+"\n\n\n"
			finished = True
	    	sumspeed[rep-2] = sp
	    	nproc = len(proc)
	    	for q in proc:
	    		print str(q)+" "
	    	print "\n\n\n"

		if rep == 2:
			sumproclist = [proc[value] for value in range(nproc)]
		else:
			for q in range(nproc):
				sumproclist[q] += proc[q]

            if l == 1: #era i == 1
                cpu_tmp = [[0 for j in range(n_threads)] for k in range(nproc)]
            for ii in range(len(sumspeed)):
	    	speed[l-1][ii] = sumspeed[ii]
            for j in range(nproc):
                cpu_tmp[j][l-1] = float(sumproclist[j])/(rep - 1)

        #cpu_usage[i] = cpu_tmp
        #plt.yticks(np.arange(0, 105, 5))
        #plt.xticks(np.arange(0, n_threads+1, 1))
        #ax = plt.gca()
        #ax.set_autoscale_on(False)
        #plt.xlabel("Number of threads")
        #plt.ylabel("Speed(mb/s)")
        #plt.grid(True)
        #plt.plot(range(1, n_threads+1) ,speed, "b.")
        #name = "./results/speed_iteration"+str(i)+".png"
        #plt.savefig(name)
        #plt.close()

	towrite = "Speed Transfer: "
	for k in range(0, len(speed)):
		for h in range(nrep):
			towrite = towrite + " " + str(speed[k][h])
		towrite += "\n"
	with open("./results/speed_iteration"+str(i)+".txt", "w") as fp:
		fp.write(towrite + "\n")
		for z in range(nproc):
			towrite1 = "cpu "+str(z+1)+" %: "
			for z1 in range(len(cpu_tmp[z])):
				towrite1 = towrite1 + " " + str(cpu_tmp[z][z1])
			fp.write(towrite1 + "\n")
		for i in range(errslist):
			if i % 20 == 0:
				fp.write("\n")
