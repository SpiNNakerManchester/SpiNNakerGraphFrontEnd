/*
 * Copyright (c) 2017-2019 The University of Manchester
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <debug.h>
#include <spin1_api.h>
#include <data_specification.h>
#include <simulation.h>

uint32_t simulation_ticks;
uint32_t infinite_run;
uint32_t time;

void timer_callback(uint time, uint unused1) {
    if (infinite_run) {
	if ((time * 2) != simulation_ticks) {
	    return;
	}
    } else {
	if (time != 2000) {
	    return;
	}
    }

    log_error("Generating Error at time %u", time);
    rt_error(RTE_SWERR);
}

void c_main(void) {
    uint32_t timer_period;

    data_specification_metadata_t *data = data_specification_get_data_address();

    if (!data_specification_read_header(data)) {
        rt_error(RTE_SWERR);
    }

    if (!simulation_initialise(
            data_specification_get_region(0, data), APPLICATION_NAME_HASH,
            &timer_period, &simulation_ticks,
            &infinite_run, &time, 1, 1)) {
        rt_error(RTE_SWERR);
    }

    spin1_set_timer_tick(timer_period);
    spin1_callback_on(TIMER_TICK, timer_callback, 0);

    simulation_run();
}
