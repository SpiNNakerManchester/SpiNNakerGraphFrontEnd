from enum import Enum

# enums associated with the ports used by the nengo tools
OUTPUT_PORT = Enum(
    value="OUTPUT_PORT",
    names=[('STANDARD', 0)])

INPUT_PORT = Enum(
    value="INPUT_PORT",
    names=[('STANDARD', 0)])

ENSEMBLE_OUTPUT_PORT = Enum(
    value="ENSEMBLE_OUTPUT_PORT",
    names=[('NEURONS', 0),
           ('LEARNT', 1)])

ENSEMBLE_INPUT_PORT = Enum(
    value="ENSEMBLE_INPUT_PORT",
    names=[('NEURONS', 0),
           ('GLOBAL_INHIBITION', 1),
           ('LEARNT', 2)])

# the max atoms per core are based off matrix sizes. these were

MAX_ROWS = 64
MAX_COLUMNS = 128

DECODERS_FLAG = "decoders"
ENCODERS_FLAG ="encoders"
APP_GRAPH_NAME = "nengo_operator_graph"
