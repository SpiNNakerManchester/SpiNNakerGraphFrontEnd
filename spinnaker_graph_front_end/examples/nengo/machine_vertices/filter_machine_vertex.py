from pacman.model.graphs.machine import MachineVertex
from spinn_front_end_common.abstract_models import AbstractHasAssociatedBinary
from spinn_front_end_common.abstract_models.impl import \
    MachineDataSpecableVertex
from enum import Enum


class FilterMachineVertex(
        MachineVertex, MachineDataSpecableVertex, AbstractHasAssociatedBinary):
    """Portion of the rows of the transform assigned to a parallel filter
    group, represents the load assigned to a single processing core.
    """

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('KEYS', 1),
               ('INPUT_FILTERS', 2),
               ('INPUT_ROUTING', 3),
               ('TRANSFORM', 4)])

    def __init__(self, size_in, max_cols, max_row):
