APP = tensorFlow_operation

SOURCES = tensorFlow_operation.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

CFLAGS += -DSPINNAKER

include $(SPINN_DIRS)/make/local.mk