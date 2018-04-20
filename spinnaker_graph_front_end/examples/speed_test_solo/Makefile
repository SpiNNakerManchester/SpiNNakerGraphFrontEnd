# If SPINN_DIRS is not defined, this is an error!
ifndef SPINN_DIRS
    $(error SPINN_DIRS is not set.  Please define SPINN_DIRS (possibly by running "source setup" in the spinnaker package folder))
endif

APP = packet_gatherer_cheat
BUILD_DIR = build/
SOURCES = packet_gatherer_cheat.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

include $(SPINN_DIRS)/make/local.mk
