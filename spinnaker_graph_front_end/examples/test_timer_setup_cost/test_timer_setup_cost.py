import spinnaker_graph_front_end as front_end

from spinnaker_graph_front_end.examples.hello_world.hello_world_vertex\
    import HelloWorldVertex
import time
import os

front_end.setup(
    n_chips_required=2, model_binary_folder=os.path.dirname(__file__))

front_end.add_machine_vertex(HelloWorldVertex, {}, label="Hello World")

front_end.run(10)

extra_monitor_vertices = front_end.globals_variables.\
    get_simulator()._last_run_outputs['MemoryExtraMonitorVertices']
extra_monitor_gatherers = front_end.globals_variables.\
    get_simulator()._last_run_outputs[
        'MemoryMCGatherVertexToEthernetConnectedChipMapping']
transceiver = front_end.transceiver()
placements = front_end.placements()


start = float(time.time())
receiver = extra_monitor_gatherers[0, 0]
receiver.set_cores_for_data_streaming(
                    transceiver=transceiver, placements=placements,
                    extra_monitor_cores_for_router_timeout=(
                        extra_monitor_vertices))
receiver.unset_cores_for_data_streaming(
                    transceiver=transceiver, placements=placements,
                    extra_monitor_cores_for_router_timeout=(
                        extra_monitor_vertices))
end = float(time.time())

print "took {} seconds to set and unset the routing timeout".format(
    float(end - start))

# end sim
front_end.stop()
