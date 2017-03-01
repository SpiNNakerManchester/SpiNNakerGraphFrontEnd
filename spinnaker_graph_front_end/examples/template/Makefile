# If SPINN_DIRS is not defined, this is an error!
ifndef SPINN_DIRS
    $(error SPINN_DIRS is not set.  Please define SPINN_DIRS (possibly by running "source setup" in the spinnaker package folder))
endif

# TODO: Rename to suit your application 
APP = c_template_vertex

BUILD_DIR = build/

# TODO: Replace with your source code files
SOURCES = c_template_vertex.c

MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR := $(dir $(MAKEFILE_PATH))
SOURCE_DIR := $(abspath $(CURRENT_DIR))
SOURCE_DIRS += $(SOURCE_DIR)
APP_OUTPUT_DIR := $(abspath $(CURRENT_DIR))/

include $(SPINN_DIRS)/make/SpiNNFrontEndCommon.mk
