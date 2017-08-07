from six import add_metaclass

from spinn_utilities.abstract_base import AbstractBase
# from spinn_utilities.abstract_base import abstractproperty
# from spinn_utilities.abstract_base import abstractmethod

from spinn_front_end_common.utilities import SimulatorInterface


@add_metaclass(AbstractBase)
class GraphFrontEndSimulatorInterface(SimulatorInterface):

    __slots__ = ()
