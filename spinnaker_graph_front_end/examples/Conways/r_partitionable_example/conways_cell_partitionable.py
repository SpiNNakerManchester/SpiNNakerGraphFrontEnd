
from pacman.model.graph.abstract_partitionable_vertex import \
    AbstractPartitionableVertex


class ConwayCell(AbstractPartitionableVertex):
    """
    cell which represents a cell within the 2 d fabric
    """

    def __init__(self, n_atoms, constraints, label):

        AbstractPartitionableVertex.__init__(
            self, n_atoms=n_atoms, constraints=constraints, label=label,
            max_atoms_per_core=200)

    def get_cpu_usage_for_atoms(self, vertex_slice, graph):
        return vertex_slice.n_atoms * 0

    def get_dtcm_usage_for_atoms(self, vertex_slice, graph):
        return vertex_slice.n_atoms * 0

    def model_name(self):
        return "ConwaysPartitionableCell"

    def get_sdram_usage_for_atoms(self, vertex_slice, graph):
        return vertex_slice.n_atoms * 0

    def create_subvertex(self, vertex_slice, resources_required, label=None,
                             constraints=None):
        return ConwaysPartitionedVertex(
            label=label, resources_required=resources_required,
            constraints=constraints)


