APP = arg_max_nd

SOURCES = arg_max_nd.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

CFLAGS += -DSPINNAKER

include $(SPINN_DIRS)/make/local.mk