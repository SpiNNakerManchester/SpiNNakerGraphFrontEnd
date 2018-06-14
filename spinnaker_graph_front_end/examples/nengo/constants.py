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
           ('LEARNT', 2),
           ('LEANING_RULE', 3)])

# the max atoms per core are based off matrix sizes. these were
MAX_ROWS = 64
MAX_COLUMNS = 128

# flag constants used around the codebase
DECODERS_FLAG = "decoders"
DECODER_OUTPUT_FLAG = "decoded_output"
RECORD_OUTPUT_FLAG = "output"
RECORD_SPIKES_FLAG = "spikes"
RECORD_VOLTAGE_FLAG = "voltage"
ENCODERS_FLAG = "encoders"
APP_GRAPH_NAME = "nengo_operator_graph"
INTER_APP_GRAPH_NAME = "nengo_operator_graph_par_way_interposers"
MACHINE_GRAPH_LABEL = "machine graph"

# sdp ports used by c code, to track with fec sdp ports.
SDP_PORTS = Enum(
    value="SDP_PORTS_READ_BY_C_CODE",
    names=[("SDP_RECEIVER", 6)])
