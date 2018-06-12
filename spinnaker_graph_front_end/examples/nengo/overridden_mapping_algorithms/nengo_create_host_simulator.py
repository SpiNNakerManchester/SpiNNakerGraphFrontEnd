import nengo

def _create_host_sim(self, host_network, dt):
    # Build the host simulator
    host_sim = nengo.Simulator(host_network, dt=dt)
    return host_sim