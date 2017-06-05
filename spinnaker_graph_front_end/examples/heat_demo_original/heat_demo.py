"""
heat demo main entrance allows users to run the heat demo on the tool chain
"""

from pacman.model.constraints.placer_constraints\
    .placer_chip_and_core_constraint import PlacerChipAndCoreConstraint
from pacman.model.graphs.machine.machine_vertex import MachineVertex
from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.resources.iptag_resource import IPtagResource
from pacman.executor.injection_decorator import inject_items

from spinn_front_end_common.abstract_models\
    .abstract_generates_data_specification \
    import AbstractGeneratesDataSpecification
import os
import platform
import subprocess
from threading import Thread
from spinn_front_end_common.utility_models.live_packet_gather_machine_vertex \
    import LivePacketGatherMachineVertex
from spinnman.messages.eieio.eieio_type import EIEIOType
from spinn_front_end_common.utilities.utility_objs.executable_start_type \
    import ExecutableStartType
from spinn_front_end_common.abstract_models.abstract_has_associated_binary \
    import AbstractHasAssociatedBinary

# graph front end imports
import spinnaker_graph_front_end as front_end
from spinnaker_graph_front_end import MachineEdge

import sys


_PARTITION_NAME = "Heat"
_STOP_PARTITION = "Stop"
_PAUSE_PARTITION = "Pause"
_RESUME_PARTITION = "Resume"
_TEMP_NORTH_PARTITION = "TempNorth"
_TEMP_SOUTH_PARTITION = "TempSouth"
_TEMP_EAST_PARTITION = "TempEast"
_TEMP_WEST_PARTITION = "TempWest"


class HeatDemoVertex(
        MachineVertex, AbstractHasAssociatedBinary,
        AbstractGeneratesDataSpecification):

    def __init__(
            self, heat_x, heat_y, is_northernmost=False, is_southernmost=False,
            is_easternmost=False, is_westernmost=False, tag=None,
            ip_address="localhost", port=None):
        MachineVertex.__init__(self, label="{}, {}".format(heat_x, heat_y))

        self._heat_x = heat_x
        self._heat_y = heat_y

        self._is_northernmost = is_northernmost
        self._is_southernmost = is_southernmost
        self._is_easternmost = is_easternmost
        self._is_westernmost = is_westernmost
        self._tag = tag
        self._ip_address = ip_address
        self._port = port

        self._north_vertex = None
        self._south_vertex = None
        self._east_vertex = None
        self._west_vertex = None

        self._control_vertex = None

    def set_north_vertex(self, north_vertex):
        if self._north_vertex is not None:
            raise Exception("North vertex already set")
        self._north_vertex = north_vertex

    def set_south_vertex(self, south_vertex):
        if self._south_vertex is not None:
            raise Exception("South vertex already set")
        self._south_vertex = south_vertex

    def set_east_vertex(self, east_vertex):
        if self._east_vertex is not None:
            raise Exception("East vertex already set")
        self._east_vertex = east_vertex

    def set_west_vertex(self, west_vertex):
        if self._west_vertex is not None:
            raise Exception("West vertex already set")
        self._west_vertex = west_vertex

    def set_control_vertex(self, control_vertex):
        if self._control_vertex is not None:
            raise Exception("Control vertex already set")
        self._control_vertex = control_vertex

    @property
    def resources_required(self):
        return ResourceContainer(
            iptags=[IPtagResource(
                self._ip_address, self._port, False, self._tag, "Heat")])

    def get_binary_file_name(self):
        return "heat_demo.aplx"

    def get_binary_start_type(self):
        return ExecutableStartType.SYNC

    @inject_items({
        "routing_infos": "MemoryRoutingInfos"
    })
    def generate_data_specification(
            self, spec, placement, routing_infos):

        # Reserve enough space for the keys (5), flags (4) and controls (7)
        spec.reserve_memory_region(0, 16 * 4)
        spec.switch_write_focus(0)

        my_key = routing_infos.get_first_key_from_pre_vertex(
            self, _PARTITION_NAME)
        north_key = 0xFFFFFFFF
        if self._north_vertex is not None:
            north_key = routing_infos.get_first_key_from_pre_vertex(
                self._north_vertex, _PARTITION_NAME)
        south_key = 0xFFFFFFFF
        if self._south_vertex is not None:
            south_key = routing_infos.get_first_key_from_pre_vertex(
                self._south_vertex, _PARTITION_NAME)
        east_key = 0xFFFFFFFF
        if self._east_vertex is not None:
            east_key = routing_infos.get_first_key_from_pre_vertex(
                self._east_vertex, _PARTITION_NAME)
        west_key = 0xFFFFFFFF
        if self._west_vertex is not None:
            west_key = routing_infos.get_first_key_from_pre_vertex(
                self._west_vertex, _PARTITION_NAME)

        spec.write_value(my_key)
        spec.write_value(north_key)
        spec.write_value(south_key)
        spec.write_value(east_key)
        spec.write_value(west_key)
        spec.write_value(1 if self._is_northernmost else 0)
        spec.write_value(1 if self._is_southernmost else 0)
        spec.write_value(1 if self._is_easternmost else 0)
        spec.write_value(1 if self._is_westernmost else 0)

        control_vertex = self._control_vertex
        if self._control_vertex is None:
            control_vertex = self

        stop_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _STOP_PARTITION)
        pause_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _PAUSE_PARTITION)
        resume_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _RESUME_PARTITION)
        temp_north_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _TEMP_NORTH_PARTITION)
        temp_south_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _TEMP_SOUTH_PARTITION)
        temp_east_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _TEMP_EAST_PARTITION)
        temp_west_key = routing_infos.get_first_key_from_pre_vertex(
            control_vertex, _TEMP_WEST_PARTITION)

        spec.write_value(stop_key)
        spec.write_value(pause_key)
        spec.write_value(resume_key)
        spec.write_value(temp_north_key)
        spec.write_value(temp_south_key)
        spec.write_value(temp_east_key)
        spec.write_value(temp_west_key)

        spec.end_specification()


n_chips_required = None
visualiser_port = 17894
if front_end.is_allocated_machine():
    n_chips_required = (5 * 48) + 1


# set up the front end and ask for the detected machines dimensions
front_end.setup(
    model_binary_module=sys.modules[__name__],
    n_chips_required=n_chips_required)
machine = front_end.machine()
boot_chip = machine.boot_chip

# Create a list of lists of vertices (x * 4) by (y * 4)
# (for 16 cores on a chip - missing cores will have missing vertices)
max_x_element_id = (machine.max_chip_x + 1) * 4
max_y_element_id = (machine.max_chip_y + 1) * 4
vertices = [
    [None for j in range(max_y_element_id)]
    for i in range(max_x_element_id)
]

live_output_vertex = LivePacketGatherMachineVertex(
    label="LiveOutput", message_type=EIEIOType.KEY_PAYLOAD_32_BIT,
    payload_as_time_stamps=False, use_payload_prefix=False,
    ip_address="localhost")

control_vertex = None
for x in range(0, max_x_element_id):
    for y in range(0, max_y_element_id):

        chip_x = x / 4
        chip_y = y / 4
        core_x = x % 4
        core_y = y % 4
        core_p = ((core_x * 4) + core_y) + 1

        # Add an element if the chip and core exists
        chip = machine.get_chip_at(chip_x, chip_y)
        if chip is not None:
            core = chip.get_processor_with_id(core_p)
            if (core is not None and not core.is_monitor):
                element = HeatDemoVertex(
                    is_northernmost=(y + 1 == max_y_element_id),
                    is_southernmost=(y == 0),
                    is_easternmost=(x + 1 == max_x_element_id),
                    is_westernmost=(x == 0),
                    port=visualiser_port)
                vertices[x][y] = element
                vertices[x][y].add_constraint(
                    PlacerChipAndCoreConstraint(chip_x, chip_y, core_p))
                front_end.add_machine_vertex_instance(element)

                if control_vertex is None:
                    control_vertex = element
                else:
                    vertices[x][y].set_control_vertex(control_vertex)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _STOP_PARTITION)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _PAUSE_PARTITION)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _RESUME_PARTITION)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _TEMP_NORTH_PARTITION)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _TEMP_SOUTH_PARTITION)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _TEMP_EAST_PARTITION)
                    front_end.add_machine_edge_instance(
                        MachineEdge(control_vertex, element),
                        _TEMP_WEST_PARTITION)

# build edges
receive_labels = list()
for x in range(0, max_x_element_id):
    for y in range(0, max_y_element_id):

        if vertices[x][y] is not None:

            # Add a north link if not at the top
            if (y + 1) < max_y_element_id and vertices[x][y + 1] is not None:
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[x][y], vertices[x][y + 1]),
                    _PARTITION_NAME)
                vertices[x][y].set_north_vertex(vertices[x][y + 1])

            # Add an east link if not at the right
            if (x + 1) < max_x_element_id and vertices[x + 1][y] is not None:
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[x][y], vertices[x + 1][y]),
                    _PARTITION_NAME)
                vertices[x][y].set_east_vertex(vertices[x + 1][y])

            # Add a south link if not at the bottom
            if (y - 1) >= 0 and vertices[x][y - 1] is not None:
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[x][y - 1], vertices[x][y - 1]),
                    _PARTITION_NAME)
                vertices[x][y].set_south_vertex(vertices[x][y - 1])

            # Add a west link if not at the left
            if (x - 1) >= 0 and vertices[x - 1][y] is not None:
                front_end.add_machine_edge_instance(
                    MachineEdge(vertices[x][y], vertices[x - 1][y]),
                    _PARTITION_NAME)
                vertices[x][y].set_west_vertex(vertices[x - 1][y])

visualiser = None
if sys.platform.startswith("win32"):
    visualiser = "visualiser.exe"
elif sys.platform.startswith("darwin"):
    visualiser = "visualiser_osx"
elif sys.platform.startswith("linux"):
    if platform.machine() == "x86_64":
        visualiser = "visualiser_linux"
    elif platform.machine() == "i386":
        visualiser = "visualiser_linux"
    elif platform.machine() is None:
        print "Can't diagnose the bit size of the machine. " \
              "Running 32 bit visualiser."
        visualiser = "visualiser_linux"
    else:
        print "I do not recognise the bit size of the machine. " \
              "Will use 32 bit visualiser."
        visualiser = "visualiser_linux"
else:
    raise Exception("Unknown platform {}".format(sys.platform))

visualiser = os.path.abspath(os.path.join(
    os.path.dirname(__file__), visualiser))


def read_output(visualiser, out):
    while visualiser.poll() is None:
        line = out.readline()
        if line:
            print line
    print "Visualiser exited - quitting"
    try:
        front_end.stop()
    except:
        pass
    os._exit(0)


ini_file = open("heatmap.ini", "w")
ini_file.write("simparams = \"HEATMAP\";\n")
ini_file.write("HEATMAP =\n")
ini_file.write("{\n")
ini_file.write("TITLE = \"Heat Demo - Live SpiNNaker Plot\";\n")
ini_file.write("XDIMENSIONS={};\n".format(max_x_element_id))
ini_file.write("EACHCHIPX=4;\n")
ini_file.write("YDIMENSIONS={};\n".format(max_y_element_id))
ini_file.write("EACHCHIPY=4;\n")
ini_file.write("PLAYPAUSEEXIT=0;\n")
ini_file.write("INTERACTION=1;\n")
ini_file.write("DISPLAYMINIPLOT=0;\n")
ini_file.write("WINHEIGHT=600;\n")
ini_file.write("WINWIDTH=550;\n")
ini_file.write("KEYWIDTH=50;\n")
ini_file.write("DISPLAYKEY=1;\n")
ini_file.write("};")
ini_file.close()

print "Executing", visualiser
vis_exec = subprocess.Popen(
    args=[visualiser, "-c", "heatmap.ini", "-ip", boot_chip.ip_address],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
Thread(target=read_output, args=[vis_exec, vis_exec.stdout]).start()

front_end.run()
