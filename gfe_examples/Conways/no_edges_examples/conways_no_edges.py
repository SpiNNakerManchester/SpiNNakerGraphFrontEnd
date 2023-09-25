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

import spinnaker_graph_front_end as front_end
from gfe_examples.Conways.no_edges_examples.conways_basic_cell import (
    ConwayBasicCell)


# set up the front end and ask for the detected machines dimensions
front_end.setup()

for count in range(0, 60):
    front_end.add_machine_vertex_instance(ConwayBasicCell(f"cell{count}"))

front_end.run(1)
front_end.stop()
