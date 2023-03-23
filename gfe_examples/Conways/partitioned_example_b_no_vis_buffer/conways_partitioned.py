# Copyright (c) 2016 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from spinn_utilities.config_holder import get_config_bool
from pacman.model.graphs.machine import MachineEdge
import spinnaker_graph_front_end as front_end
from gfe_examples.Conways.partitioned_example_b_no_vis_buffer.\
    conways_basic_cell import (
        ConwayBasicCell)

runtime = 50
MAX_X_SIZE_OF_FABRIC = 7
MAX_Y_SIZE_OF_FABRIC = 7
n_chips = (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC) // 15

# set up the front end and ask for the detected machines dimensions
front_end.setup(
    n_chips_required=n_chips, model_binary_folder=os.path.dirname(__file__))

# figure out if machine can handle simulation
cores = front_end.get_number_of_available_cores_on_machine()
if cores <= (MAX_X_SIZE_OF_FABRIC * MAX_Y_SIZE_OF_FABRIC):
    raise KeyError("Don't have enough cores to run simulation")

# contain the vertices for the connection aspect
vertices = dict()

active_states = [(2, 2), (3, 2), (3, 3), (4, 3), (2, 4)]

# build vertices
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):
        vert = ConwayBasicCell(
            f"cell{(x * MAX_X_SIZE_OF_FABRIC) + y}",
            (x, y) in active_states)
        vertices[x, y] = vert
        front_end.add_machine_vertex_instance(vert)

# verify the initial state
output = ""
for y in range(MAX_X_SIZE_OF_FABRIC - 1, 0, -1):
    for x in range(0, MAX_Y_SIZE_OF_FABRIC):
        output += "X" if vertices[x, y].state else " "
    output += "\n"
print(output)
print("\n\n")

# build edges
for x in range(0, MAX_X_SIZE_OF_FABRIC):
    for y in range(0, MAX_Y_SIZE_OF_FABRIC):

        positions = [
            (x, (y + 1) % MAX_Y_SIZE_OF_FABRIC, "N"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
                (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NE"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC, y, "E"),
            ((x + 1) % MAX_X_SIZE_OF_FABRIC,
                (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SE"),
            (x, (y - 1) % MAX_Y_SIZE_OF_FABRIC, "S"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
                (y - 1) % MAX_Y_SIZE_OF_FABRIC, "SW"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC, y, "W"),
            ((x - 1) % MAX_X_SIZE_OF_FABRIC,
                (y + 1) % MAX_Y_SIZE_OF_FABRIC, "NW")]

        for (dest_x, dest_y, compass) in positions:
            front_end.add_machine_edge_instance(
                MachineEdge(
                    vertices[x, y], vertices[dest_x, dest_y],
                    label=compass), ConwayBasicCell.PARTITION_ID)
            vertices[dest_x, dest_y].add_neighbour(vertices[x, y])

# run the simulation
front_end.run(runtime)

# get recorded data
recorded_data = dict()

if not get_config_bool("Machine", "virtual_board"):
    # get the data per vertex
    for x in range(0, MAX_X_SIZE_OF_FABRIC):
        for y in range(0, MAX_Y_SIZE_OF_FABRIC):
            recorded_data[x, y] = vertices[x, y].get_data()

    # visualise it in text form (bad but no vis this time)
    for time in range(0, runtime):
        print(f"at time {time}")
        output = ""
        for y in range(MAX_X_SIZE_OF_FABRIC - 1, 0, -1):
            for x in range(0, MAX_Y_SIZE_OF_FABRIC):
                output += "X" if recorded_data[x, y][time] else " "
            output += "\n"
        print(output)
        print("\n\n")

# clear the machine
front_end.stop()
