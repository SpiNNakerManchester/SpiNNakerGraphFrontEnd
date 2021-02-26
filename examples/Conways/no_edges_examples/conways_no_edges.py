# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import spinnaker_graph_front_end as front_end
from examples.Conways.no_edges_examples.conways_basic_cell import (
    ConwayBasicCell)


# set up the front end and ask for the detected machines dimensions
front_end.setup()

for count in range(0, 60):
    front_end.add_machine_vertex_instance(
        ConwayBasicCell("cell{}".format(count)))

front_end.run(1)
front_end.stop()
