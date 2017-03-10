from pacman.model.resources import ResourceContainer
from pacman.model.graphs.machine import SimpleMachineVertex
from spinn_front_end_common.abstract_models.abstract_has_associated_binary\
    import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models\
    .abstract_generates_data_specification \
    import AbstractGeneratesDataSpecification
from spinn_front_end_common.abstract_models.abstract_starts_synchronized\
    import AbstractStartsSynchronized


class TestNormalVertex(
        SimpleMachineVertex, AbstractHasAssociatedBinary,
        AbstractStartsSynchronized, AbstractGeneratesDataSpecification):

    def __init__(self, run_duration):
        SimpleMachineVertex.__init__(self, ResourceContainer())
        self._run_duration = run_duration

    def get_binary_file_name(self):
        return "test_normal_binary.aplx"

    def generate_data_specification(self, spec, placement):
        spec.reserve_memory_region(0, 4)
        spec.switch_write_focus(0)
        spec.write_value(data=self._run_duration)
        spec.end_specification()
