from six import add_metaclass
from spinn_utilities.abstract_base import AbstractBase
from spinn_front_end_common.utilities import SimulatorInterface
# from spinn_utilities.abstract_base import (
#     abstractproperty, abstractmethod)


@add_metaclass(AbstractBase)
class GraphFrontEndSimulatorInterface(SimulatorInterface):

    __slots__ = ()
