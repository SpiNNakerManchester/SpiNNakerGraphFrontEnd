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

from spinnaker_testbase import RootScriptBuilder


class ScriptBuilder(RootScriptBuilder):
    """
    This file will recreate the test_scripts.py file

    To skip the too_long scripts run this script with a parameter
    """

    def build_scripts(self) -> None:
        # create_test_scripts supports test that are too long or exceptions

        # It does not matter if this picks up classes with no main
        # For those it just acts like test_import_all does
        self.create_test_scripts(
            ["gfe_examples"])


if __name__ == '__main__':
    builder = ScriptBuilder()
    builder.build_scripts()
