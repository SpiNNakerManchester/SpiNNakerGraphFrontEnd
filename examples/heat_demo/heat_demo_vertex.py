#pacman inports
from pacman.model.abstract_classes.abstract_partitionable_vertex import \
    AbstractPartitionableVertex

#spinn front end common imports
from spinn_front_end_common.abstract_models.\
    abstract_data_specable_vertex import \
    AbstractDataSpecableVertex


class HeatDemoVertex(AbstractPartitionableVertex,
                     AbstractDataSpecableVertex):

    CORE_APP_IDENTIFIER = 0xABCD
    _model_based_max_atoms_per_core = 1
    _model_n_atoms = 1

    def __init__(self, label, constraints, machine_time_step,
                 time_scale_factor):
        AbstractPartitionableVertex.__init__(
            self, label=label,
            max_atoms_per_core=HeatDemoVertex._model_based_max_atoms_per_core,
            n_atoms=HeatDemoVertex._model_n_atoms, constraints=constraints)
        AbstractDataSpecableVertex.__init__(
            self, label=label, n_atoms=HeatDemoVertex._model_n_atoms,
            machine_time_step=machine_time_step,
            timescale_factor=time_scale_factor)

    def get_binary_file_name(self):
        return "heat_demo.aplx"

    def model_name(self):
        return "Heat_Demo_Vertex"

    def get_cpu_usage_for_atoms(self, vertex_slice, graph):
        return 2

    def get_dtcm_usage_for_atoms(self, vertex_slice, graph):
        return 2

    def generate_data_spec(self, subvertex, placement, sub_graph, graph,
                           routing_info, hostname, graph_subgraph_mapper,
                           report_folder, write_text_specs,
                           application_run_time_folder):
        pass

    def get_sdram_usage_for_atoms(self, vertex_slice, graph):
        return 12