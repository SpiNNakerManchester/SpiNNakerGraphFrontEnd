# Copyright (c) 2017-2019 The University of Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import unittest
from spinn_front_end_common.utilities import globals_variables


class TestLoggerExample(unittest.TestCase):

    def setUp(self):
        globals_variables.unset_simulator()

    def near_equals(self, a, b):
        diff = a - b
        if diff == 0:
            return True
        ratio = diff / a
        return abs(ratio) < 0.0000001

    def check_line(self, line):
        print(line)
        if "logger_example.c" not in line:
            print("OTHER")
            return
        parts = line.split(":")
        if len(parts) != 4:
            print("size {}".format(len(parts)))
            return
        check = parts[3]
        print(check)
        if "==" in check:
            tokens = check.split("==")
            self.assertEquals(tokens[0].strip(), tokens[1].strip())
            print("pass")
        elif "=" in check:
            tokens = check.split("=")
            self.assertEquals(
                float(tokens[0].strip()), float(tokens[1].strip()))
            print("pass")
        elif "~" in check:
            tokens = check.split("~")
            assert self.near_equals(
                float(tokens[0].strip()), float(tokens[1].strip()))
            print("pass")
        else:
            print("todo")

    def test_logger_example(self):
        import spinnaker_graph_front_end.examples.logger_example as le_dir
        class_file = le_dir.__file__
        path = os.path.dirname(os.path.abspath(class_file))
        print(path)
        os.chdir(path)
        import spinnaker_graph_front_end.examples.logger_example.logger_example  # NOQA
        report_directory = globals_variables.get_simulator().\
            _report_default_directory
        log_path = os.path.join(report_directory, "provenance_data",
                                "iobuf_for_chip_0_0_processor_id_3.txt")
        with open(log_path) as log_file:
            for line in log_file:
                self.check_line(line)
