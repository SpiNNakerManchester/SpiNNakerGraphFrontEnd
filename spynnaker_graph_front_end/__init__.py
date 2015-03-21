from spynnaker_graph_front_end import model_binaries

_spinnaker = None
_executable_finder = None


def _init_module():
    import logging
    import os
    from spinn_front_end_common.interface.executable_finder \
        import ExecutableFinder
    global _executable_finder

    _executable_finder = ExecutableFinder(model_binaries.__file__)
    # Register this path with SpyNNaker
    logging.info("recording where SpiNNakerGraphFrontEnd model binaries reside")

_init_module()


def setup():
    from spynnaker_graph_front_end.spinnaker_graph_front_end import \
        SpiNNakerGraphFrontEnd
    global _executable_finder
    global _spinnaker
    if _executable_finder is None:
        _init_module()
    # set up the spinnaker object
    _spinnaker = SpiNNakerGraphFrontEnd()


def run(duration=None):
    """

    """
    import sys
    global _spinnaker

    if duration is None:
        duration = sys.maxint
    _spinnaker.run(duration)


def end(stop_on_board=True):
    """
    Do any necessary cleaning up before exiting.

    Unregisters the controller
    """
    global _spinnaker
    global _executable_finder

    _spinnaker.stop(stop_on_board)
    _spinnaker = None
    _executable_finder = None


def read_xml_file(file_path):
    """
    helper method for people who use this as an import.
    reads a xml file and translates it into a graph and partitioned graph
    (if required)
    :param file_path: the file path in absulete form
    :return: None
    """
    global _spinnaker
    _spinnaker.read_xml_file(file_path)


# noinspection PyPep8Naming
def Vertex(cellclass, cellparams, label=None):
    global _spinnaker
    return _spinnaker.add_vertex(cellclass, cellparams, label)


# noinspection PyPep8Naming
def Edge(pre_vertex, post_vertex, constraints, label):
    global _spinnaker
    return _spinnaker.add_edge(pre_vertex, post_vertex, constraints, label)