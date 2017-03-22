from pacman.model.resources.resource_container import ResourceContainer
from pacman.model.graphs.machine.impl.simple_machine_vertex \
    import SimpleMachineVertex

from spinn_front_end_common.abstract_models.abstract_has_associated_binary\
    import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models\
    .abstract_generates_data_specification \
    import AbstractGeneratesDataSpecification
from spinn_front_end_common.utilities.utility_objs.executable_start_type \
    import ExecutableStartType


class TestNormalVertex(
        SimpleMachineVertex, AbstractHasAssociatedBinary,
        AbstractGeneratesDataSpecification):

    def __init__(self, run_duration):
        SimpleMachineVertex.__init__(self, ResourceContainer())
        self._run_duration = run_duration

    def get_binary_file_name(self):
        return "test_normal_binary.aplx"

    def get_binary_start_type(self):
        return ExecutableStartType.SYNC

    def generate_data_specification(self, spec, placement):
        spec.reserve_memory_region(0, 4)
        spec.switch_write_focus(0)
        spec.write_value(data=self._run_duration)
        spec.end_specification()
