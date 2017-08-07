APP = test_rte_start
APP_OUTPUT_DIR = ./
BUILD_DIR = build/
SOURCE_DIRS += $(abspath .)
SOURCES = test_rte_start.c

# The spinnaker_tools standard makefile
include $(SPINN_DIRS)/make/Makefile.SpiNNFrontEndCommon
