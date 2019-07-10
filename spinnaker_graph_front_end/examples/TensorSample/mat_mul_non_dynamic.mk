APP = mat_mul_non_dynamic

SOURCES = mat_mul_non_dynamic.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

CFLAGS += -DSPINNAKER

include $(SPINN_DIRS)/make/local.mk