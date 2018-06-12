

class ModelWrapper(object):
    """
    glue object to avoid a god object
    """

    __slots__ = [
        # the set of app verts from nengo objects. named params from nengo
        # interface
        "_params",

        # ????????????
        "_decoder_cache"
    ]

    def __init__(self, nengo_to_app_graph_map, decoder_cache):
        self._params = nengo_to_app_graph_map
        self._decoder_cache = decoder_cache

    @property
    def params(self):
        return self._params

    @property
    def decoder_cache(self):
        return self._decoder_cache

