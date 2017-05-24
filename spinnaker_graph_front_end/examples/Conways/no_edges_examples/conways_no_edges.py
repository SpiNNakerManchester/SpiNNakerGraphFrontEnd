import spinnaker_graph_front_end as front_end

from spinnaker_graph_front_end.examples.Conways.no_edges_examples.\
    conways_basic_cell import ConwayBasicCell

# Can't instantiate abstract class ConwayBasicCell with abstract methods
# resources_required
def run_broken():
    # set up the front end and ask for the detected machines dimensions
    front_end.setup()

    for count in range(0, 60):
        front_end.add_machine_vertex_instance(
            ConwayBasicCell("cell{}".format(count)))

    front_end.run(1)
    front_end.stop()


if __name__ == '__main__':
    run_broken()
