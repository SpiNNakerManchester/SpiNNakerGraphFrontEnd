APP = test_rte_during_run
APP_OUTPUT_DIR = ./
BUILD_DIR = build/
SOURCE_DIRS += $(abspath .)
SOURCES = test_rte_during_run.c

# The spinnaker_tools standard makefile
include $(SPINN_DIRS)/make/Makefile.SpiNNFrontEndCommon
