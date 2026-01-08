# Copyright (c) 2016 The University of Manchester
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

CUR_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
FEC_INSTALL_DIR := $(strip $(if $(FEC_INSTALL_DIR), $(FEC_INSTALL_DIR), $(abspath $(CUR_DIR)/../../../../SpiNNFrontEndCommon/c_common/front_end_common_lib)))

APP = conways_cell
SOURCES = conways_cell.c

APP_OUTPUT_DIR := $(CUR_DIR)/
# key for the database in this APP_OUTPUT_DIR
DATABASE_KEY = V

include $(FEC_INSTALL_DIR)/make/fec.mk

clean:
	${RM} $(APP_OUTPUT_DIR)logs*.sqlite3 $(APP_OUTPUT_DIR)*.aplx
	$(RM) -r $(CUR_DIR)/build
