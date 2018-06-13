from six import add_metaclass

from pacman.model.graphs import AbstractVertex
from pacman.model.graphs.common import ConstrainedObject
from spinn_utilities.abstract_base import AbstractBase, abstractmethod
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo.abstracts.abstract_nengo_object import \
    AbstractNengoObject


@add_metaclass(AbstractBase)
class AbstractNengoApplicationVertex(
        ConstrainedObject, AbstractVertex, AbstractNengoObject):

    __slots__ = [
        # the label of this vertex
        '_label'
    ]

    def __init__(self, label, rng, constraints=None):
        ConstrainedObject.__init__(self, constraints)
        AbstractVertex.__init__(self)
        AbstractNengoObject.__init__(self, rng)
        self._label = label

    @property
    @overrides(AbstractVertex.label)
    def label(self):
        return self._label

    def __str__(self):
        return self.label

    def __repr__(self):
        return "ApplicationVertex(label={}, constraints={}, seed={}".format(
            self.label, self.constraints, self._seed)

    @abstractmethod
    def create_machine_vertices(self):
        """
        
        :return: 
        """
