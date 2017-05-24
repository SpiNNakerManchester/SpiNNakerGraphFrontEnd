import spinnaker_graph_front_end as front_end


# spinn_front_end_common.utilities.exceptions.ConfigurationException:
# There needs to be a graph which contains at least one vertex for
# the tool chain to map anything.
def run_broken():
    # set up the front end and ask for the detected machines dimensions
    front_end.setup()

    front_end.run()
    front_end.stop()


if __name__ == '__main__':
    run_broken()
