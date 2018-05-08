APP = test_run_too_long
SOURCES = test_run_too_long.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

include $(SPINN_DIRS)/make/local.mk
