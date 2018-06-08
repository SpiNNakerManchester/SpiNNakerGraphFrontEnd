class NengoUtiliseInterposers(object):


    def __call__(self):
        def insert_and_stack_interposers(self):
            """Get a new connection map with the passthrough nodes removed and with
            interposers inserted into the network at appropriate places, moreover
            combine compatible interposers to reduce network load at sinks.

            Returns
            -------
            ([Interposer, ...], ConnectionMap)
                A collection of new interposer operators and a new connection map
                with passthrough nodes removed and interposers introduced.
            """
            interposers, cm = self.insert_interposers()
            return cm.stack_interposers(interposers)

        def insert_interposers(self):
            """Get a new connection map with the passthrough nodes removed and with
            interposers inserted into the network at appropriate places.

            Returns
            -------
            ([Interposer, ...], ConnectionMap)
                A collection of new interposer operators and a new connection map
                with passthrough nodes removed and interposers introduced.
            """
            # Create a new connection map and a store of interposers
            interposers = list()
            cm = ConnectionMap()

            # For every clique in this connection map we identify which connections
            # to replace with interposers and then insert the modified connectivity
            # into the new connection map.
            for sources, nodes in self.get_cliques():
                # Extract all possible interposers from the clique. Interposers can
                # either replace connections from passthrough nodes or the
                # "transform" portion of the connection from an ensemble.
                possible_interposers = (
                    (node, port, conn, {s.sink_object for s in sinks})
                    for node in chain(
                    nodes, (e for e in sources if isinstance(e, EnsembleLIF))
                )
                    for port, conns in iteritems(
                    self._connections[node])
                    for conn, sinks in iteritems(conns)
                )

                # Of these possible connections determine which would benefit from
                # replacement with interposers. For these interposers build a set
                # of other potential interposers whose input depends on the output
                # of the interposer.
                potential_interposers = dict()
                for node, port, conn, sink_objects in possible_interposers:
                    _, tps = conn  # Extract the transmission parameters

                    # Determine if the interposer connects to anything
                    if not self._connects_to_non_passthrough_node(sink_objects):
                        continue

                    # For each connection look at the fan-out and fan-in vs the
                    # cost of the interposer.
                    trans = tps.full_transform(False, False)
                    mean_fan_in = np.mean(np.sum(trans != 0.0, axis=0))
                    mean_fan_out = np.mean(np.sum(trans != 0.0, axis=1))
                    interposer_fan_in = np.ceil(
                        float(trans.shape[1]) / float(128))
                    interposer_fan_out = np.ceil(
                        float(trans.shape[0]) / float(64))

                    # If the interposer would improve connectivity then add it to
                    # the list of potential interposers.
                    if (mean_fan_in > interposer_fan_in or
                                mean_fan_out > interposer_fan_out):
                        # Store the potential interposer along with a list of nodes
                        # who receive its output.
                        potential_interposers[(node, port, conn)] = [
                            s for s in sink_objects
                            if isinstance(s, PassthroughNode)
                        ]

                # Get the set of potential interposers whose input is independent
                # of the output of any other interposer.
                top_level_interposers = set(potential_interposers)
                for dependent_interposers in itervalues(potential_interposers):
                    # Subtract from the set of independent interposers any whose
                    # input node is listed in the output nodes for another
                    # interposer.
                    remove_interposers = {
                        (node, port, conn) for (node, port, conn) in
                        top_level_interposers if node in dependent_interposers
                    }
                    top_level_interposers.difference_update(remove_interposers)

                # Create an operator for all of the selected interposers
                clique_interposers = dict()
                for node, port, conn in top_level_interposers:
                    # Extract the input size
                    _, transmission_pars = conn
                    size_in = transmission_pars.size_in

                    # Create the interposer
                    clique_interposers[node, port, conn] = Filter(size_in)

                # Insert connections into the new connection map inserting
                # connections to interposers as we go and remembering those to
                # which a connection is added.
                used_interposers = set()  # Interposers who receive non-zero input
                for source in sources:
                    used_interposers.update(
                        self._copy_connections_from_source(
                            source=source, target_map=cm,
                            interposers=clique_interposers
                        )
                    )

                # Insert connections from the new interposers.
                for (node, port, conn) in used_interposers:
                    # Get the interposer, add it to the new operators to include in
                    # the model and add its output to the new connection map.
                    interposer = clique_interposers[(node, port, conn)]
                    interposers.append(interposer)

                    # Add outgoing connections
                    self._copy_connections_from_interposer(
                        node=node, port=port, conn=conn, interposer=interposer,
                        target_map=cm
                    )

            return interposers, cm