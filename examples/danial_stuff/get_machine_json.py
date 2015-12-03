

from pacman.operations.pacman_algorithm_executor import PACMANAlgorithmExecutor
import spinnaker_graph_front_end as front_end
import os
from pacman.utilities import file_format_converters

path = "/home/alan/Documents/fileMachine"

# set up the front end
front_end.setup()

# force a transciever to be generated
dimensions = front_end.get_machine_dimensions()
transciever = front_end.get_txrx()

# generate the inputs for the algorithm
inputs = list()
inputs.append({"type": "MemoryMachine",
               "value": transciever.get_machine_details()})
inputs.append({"type": "FileMachineFilePath", "value": path})

# ask for the file machien output
outputs = list()
outputs.append("FileMachine")

algorithms = list()
algorithms.append("ConvertToFileMachine")
xml_paths = list()
xml_paths.append(os.path.join(
            os.path.dirname(file_format_converters.__file__),
            "converter_algorithms_metadata.xml"))

# create and run the exeuctor
executor = PACMANAlgorithmExecutor(algorithms, inputs, xml_paths, outputs)
executor.execute_mapping()
