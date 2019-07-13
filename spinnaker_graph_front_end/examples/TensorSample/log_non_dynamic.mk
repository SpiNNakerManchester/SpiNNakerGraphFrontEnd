APP = log_non_dynamic

SOURCES = log_non_dynamic.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

CFLAGS += -DSPINNAKER

include $(SPINN_DIRS)/make/local.mk