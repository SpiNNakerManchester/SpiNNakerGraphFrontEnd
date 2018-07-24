from pacman.model.constraints.key_allocator_constraints import \
    AbstractKeyAllocatorConstraint


class NengoKeyConstraint(AbstractKeyAllocatorConstraint):

    def __init__(self, field_enum):
        self._field_enum_value = field_enum
