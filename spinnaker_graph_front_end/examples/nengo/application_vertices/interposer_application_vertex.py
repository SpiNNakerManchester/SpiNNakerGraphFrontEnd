import math

from pacman.executor.injection_decorator import inject
from spinn_utilities.overrides import overrides
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.abstracts.\
    abstract_nengo_application_vertex import \
    AbstractNengoApplicationVertex


class InterposerApplicationVertex(AbstractNengoApplicationVertex):
    """Operator which receives values, performs filtering, applies a linear
        transform and then forwards the resultant vector(s).

        The input and output vector(s) may be sufficiently large that the load
        related to receiving all the packets, filtering the input vector, 
        applying
        the linear transform and transmitting the resultant values may be beyond
        the computational or communication capabilities of a single chip or
         core.
        The output vectors can be treated as a single large vector which is 
        split
        into smaller vectors by transmitting each component with an appropriate
        key; hence we can consider the entire operation of the filter component 
        as
        computing:

        ..math:: c[z] = \mathbf{A} b[z]

        Where **A** is the linear transform applied by the filter operator,
        :math:`b[z]` is the filtered input vector and :math:`c[z]` is the 
        nominal
        output vector.

        If **A** is of size :math:`m \times n` then *n* determines how many 
        packets
        each processing core (or group of processing cores) needs to receive and
        *m* determines how many packets each processing core (or group of cores)
        needs to transmit. To keep the number of packets received small we 
        perform
        column-wise partition of A such that:

        ..math:: c[z] = \mathbf{A_1} b_1[z] + \mathbf{A_2} b_2[z]

        Where :math:`\mathbf{A_x} b_x[z]` is the product computed by one set of
        processing cores and :math:`c[z]` is the resultant vector as 
        constructed by
        any cores which receive packets from cores implementing the filter
        operator. Note that the sum of products is computed by the receiving
         cores.
        **A** and `b` are now partitioned such that **A** is of size :math:`m
        \times (\frac{n}{2})` and `b` is of size :math:`\frac{n}{2}`; this 
        reduces
        the number of packets that need to be received by any group of cores
        implementing the filter operator.

        To reduce the number of packets which need to be transmitted by each 
        core
        we partition :math:`A_x` into rows such that:

        ..math::
            c =
            \begin{pmatrix}
              A_{1,1}~b_1 & + & A_{1,2}~b_2\\
              A_{2,1}~b_1 & + & A_{2,2}~b_2
            \end{pmatrix}

        Where, in this example, :math:`A_{x,y}` is of size :math:`\frac{m}{2}
        \times \frac{n}{2}`. Hence both the number of packets received and
        transmitted by each core has been halved, and the number of
        multiply-accumulates performed by each core has been quartered.  This
        reduction in communication and computation in the filter operator is
        achieved at the cost of requiring any operator with input `c` to 
        receive
        twice as many packets as previously (one set of packets for each
        column-wise division) and to perform some additions.
        """

    __slots__ = [
        # ?????
        "_size_in",

        #
        "_groups"
        ]

    def __init__(self, size_in, label, rng, max_cols=constants.MAX_COLUMNS,
                 max_rows=constants.MAX_ROWS):
        """Create a new parallel Filter.
        
        :param size_in:  Width of the filter (length of any incoming signals).
        :type size_in: int
        :param max_cols: Maximum number of columns and rows which may be\ 
        handled by a single processing core. The defaults (128 and 64 \
        respectively) result in the overall connection matrix being \
        decomposed such that (a) blocks are sufficiently small to be stored \
        in DTCM, (b) network traffic is reduced.
        :type max_cols: int
        :param max_rows: see max_cols
        :type max_rows: int
        :param rng: the random number generator for generating seeds
        """

        # NB: max_rows and max_cols determined by experimentation by AM and
        # some modelling by SBF.
        # Create as many groups as necessary to keep the size in of any group
        # less than max_cols.
        AbstractNengoApplicationVertex.__init__(self, label=label, rng=rng)

        self._size_in = size_in
        n_groups = int(math.ceil(size_in // max_cols))
        self._groups = tuple(FilterGroup(sl, max_rows) for sl in
                            divide_slice(slice(0, size_in), n_groups))

    @property
    def size_in(self):
        return self._size_in

    @property
    def groups(self):
        return self._groups

    def create_machine_vertices(self):
        pass

    @inject({"output_signals": "OutputSignals",
             "machine_time_step": "MachineTimeStep",
             "filter_region": "Filterregion",
             "filter_routing_region": "FilterRoutingRegion"})
    @overrides(AbstractNengoApplicationVertex.create_machine_vertices,
               additional_arguments=[
                   "output_signals", "machine_time_step", "filter_region",
                   "filter_routing_region"])
    def create_machine_vertices(
            self, output_signals, machine_time_step, filter_region,
            filter_routing_region):
        """Partition the transform matrix into groups of rows and assign each
        group of rows to a core for computation.
    
        If the group needs to be split over multiple chips (i.e., the group is
        larger than 17 cores) then partition the matrix such that any used
        chips are used in their entirety.
        """
        if OutputPort.standard not in output_signals:
            self.cores = list()
        else:
            # Get the output transform, keys and slices for this slice of the
            # filter.
            transform, keys, output_slices = \
                get_transforms_and_keys(output_signals[OutputPort.standard],
                                        self.column_slice)

            size_out = transform.shape[0]

            # Build as many vertices as required to keep the number of rows
            # handled by each core below max_rows.
            n_cores = (
                (size_out // self.max_rows) +
                (1 if size_out % self.max_rows else 0)
            )

            # Build the transform region for these cores
            transform_region = regions.MatrixRegion(
                np_to_fix(transform),
                sliced_dimension=regions.MatrixPartitioning.rows
            )

            # Build all the vertices
            self.cores = [
                FilterCore(self.column_slice, out_slice,
                           transform_region, keys, output_slices,
                           machine_timestep,
                           filter_region, filter_routing_region) for
                out_slice in divide_slice(slice(0, size_out), n_cores)
            ]

        return self.cores


    def add_constraint(self, constraint):
        pass

    @property
    def constraints(self):
        pass