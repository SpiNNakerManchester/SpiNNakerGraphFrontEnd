/*
 * Copyright (c) 2017 The University of Manchester
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#define PROFILER_ENABLED 1

//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <profiler.h>
#include <simulation.h>
#include <debug.h>

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! Spaces to write to for test
static uint32_t *sdram_space;
static uint32_t *dtcm_space;

#define SPACE_SIZE 10


//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    PROFILE_DATA
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities {
    MC_PACKET = -1,
    SDP = 0,
    DMA = 1,
    TIMER = 2,
    USER = 3
} callback_priorities;

#define WRITE_SDRAM 1
#define WRITE_DTCM  2

// -------------------------------------------------------------------


/****f*
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void update (uint ticks, uint b)
 *
 * SOURCE
 */
static void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    log_debug("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        log_info("Simulation complete.");

        // fall into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        // Finish profiling
        profiler_finalise();

        // switch to state where host is ready to read
        simulation_ready_to_read();

        return;
    }

    profiler_write_entry(PROFILER_ENTER | WRITE_SDRAM);
    for (uint32_t i = 0; i < SPACE_SIZE; i++) {
        sdram_space[i] = i;
    }
    profiler_write_entry(PROFILER_EXIT | WRITE_SDRAM);

    profiler_write_entry(PROFILER_ENTER | WRITE_DTCM);
    for (uint32_t i = 0; i < SPACE_SIZE; i++) {
        dtcm_space[i] = i;
    }
    profiler_write_entry(PROFILER_EXIT | WRITE_DTCM);
}

static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started\n");

    // Get the address this core's DTCM data starts at from SRAM
    data_specification_metadata_t *data = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(data)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // Get the timing details and set up the simulation interface
    if (!simulation_initialise(
            data_specification_get_region(SYSTEM_REGION, data),
            APPLICATION_NAME_HASH, timer_period, &simulation_ticks,
            &infinite_run, &time, SDP, DMA)) {
        return false;
    }

    profiler_init(data_specification_get_region(PROFILE_DATA, data));

    uint32_t space = SPACE_SIZE * sizeof(uint32_t);
    sdram_space = sark_xalloc(sv->sdram_heap, space, 0,
            ALLOC_LOCK + ALLOC_ID + (sark_vec->app_id << 8));
    dtcm_space = spin1_malloc(space);

    return true;
}

/****f*
 *
 * SUMMARY
 *  This function is called at application start-up.
 *  It is used to register event callbacks and begin the simulation.
 *
 * SYNOPSIS
 *  int c_main()
 *
 * SOURCE
 */
void c_main(void) {
    log_info("starting heat_demo\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_info("setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
