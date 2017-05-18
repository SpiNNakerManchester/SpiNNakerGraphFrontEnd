import spinnaker_graph_front_end as front_end


# Does not work with a spalloc machine
def do_broken():
    # set up the front end and ask for the detected machines dimensions
    front_end.setup()

    front_end.run()
    front_end.stop()


if __name__ == '__main__':
    do_broken()