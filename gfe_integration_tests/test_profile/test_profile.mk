# Copyright (c) 2017 The University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# If FEC_INSTALL_DIR is not defined, this is an error!
ifndef FEC_INSTALL_DIR
    $(error FEC_INSTALL_DIR is not set.  Please define FEC_INSTALL_DIR (possibly by running "source setup" in the spinnaker package folder))
endif

APP = test_profile
SOURCES = test_profile.c

APP_OUTPUT_DIR := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))/

# The spinnaker_tools standard makefile
include $(FEC_INSTALL_DIR)/make/fec.mk
