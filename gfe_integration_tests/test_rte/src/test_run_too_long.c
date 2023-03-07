/*
 * Copyright (c) 2017 The University of Manchester
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <debug.h>
#include <spin1_api.h>
#include <data_specification.h>
#include <simulation.h>

static uint32_t simulation_ticks;
uint32_t infinite_run;
uint32_t time;

void timer_callback(uint time, UNUSED uint unused1) {
    if (time == 1) {
        log_warning("Going to run for %u ticks", simulation_ticks + 1000000);
    }
    if (time >= simulation_ticks + 1000000) {
        spin1_exit(0);
    }
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

    log_info("Running for %u ticks", simulation_ticks);

    spin1_set_timer_tick(timer_period);
    spin1_callback_on(TIMER_TICK, timer_callback, 0);

    simulation_run();
}
