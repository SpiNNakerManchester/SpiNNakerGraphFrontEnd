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

MY_MAKEFILES = test_rte_during_run.mk test_rte_start.mk test_run_too_long.mk

all: $(MY_MAKEFILES)
	for f in $(MY_MAKEFILES); do \
		$(MAKE) -f $$f || exit $$?; \
	done

clean: $(MAKEFILES)
	for f in $(MY_MAKEFILES); do \
		$(MAKE) -f $$f clean || exit $$?; \
	done
