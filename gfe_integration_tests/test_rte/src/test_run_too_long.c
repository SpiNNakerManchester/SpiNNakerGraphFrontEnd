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

static uint32_t simulation_ticks;
uint32_t infinite_run;

void timer_callback(uint time, uint unused1) {
    if (time == 1) {
        log_warning("Going to run for %u ticks", simulation_ticks + 1000000);
    }
    if (time >= simulation_ticks + 1000000) {
        spin1_exit(0);
    }
}

void c_main() {

    uint32_t timer_period;

    data_specification_metadata_t *data = data_specification_get_data_address();

    if (!data_specification_read_header(data)) {
        rt_error(RTE_SWERR);
    }

    if (!simulation_initialise(
            data_specification_get_region(0, data), APPLICATION_NAME_HASH,
            &timer_period, &simulation_ticks,
            &infinite_run, 1, 1)) {
        rt_error(RTE_SWERR);
    }

    log_info("Running for %u ticks", simulation_ticks);

    spin1_set_timer_tick(timer_period);
    spin1_callback_on(TIMER_TICK, timer_callback, 0);

    simulation_run();
}
