import nengo

class NengoSpiNNakerApplicationGraphBuilder(object):

    def __call__(self):
        app_graph = self._generate_spinnaker_app_graph()
        nengo_graph = self._generate_nengo_graph()

    def _generate_spinnaker_app_graph(self):



    def _generate_nengo_graph(self):










    def _create_host_sim(self):
        # change node_functions to reflect time
        # TODO: improve the reference simulator so that this is not needed
        #       by adding a realtime option
        node_functions = {}
        node_info = dict(start=None)
        for node in self.io_controller.host_network.all_nodes:
            if callable(node.output):
                old_func = node.output
                if node.size_in == 0:
                    def func(t, f=old_func):
                        now = time.time()
                        if node_info['start'] is None:
                            node_info['start'] = now

                        t = (now - node_info['start']) * self.timescale
                        return f(t)
                else:
                    def func(t, x, f=old_func):
                        now = time.time()
                        if node_info['start'] is None:
                            node_info['start'] = now

                        t = (now - node_info['start']) * self.timescale
                        return f(t, x)
                node.output = func
                node_functions[node] = old_func

        # Build the host simulator
        host_sim = nengo.Simulator(
            self.io_controller.host_network, dt=self.dt)
        # reset node functions
        for node, func in node_functions.items():
            node.output = func

        return host_sim