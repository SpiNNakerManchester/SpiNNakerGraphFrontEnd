/*
 * Copyright (c) 2020-2021 The University of Manchester
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


#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

/* validates that the model being compiled does indeed contain a application
 * magic number*/
#ifndef APPLICATION_NAME_HASH
#error APPLICATION_NAME_HASH was undefined.  Make sure you define this\
    constant
#endif

//! values for the priority for each callback
typedef enum callback_priorities {
    TIMER = 2, SDP = 0, DMA = 1,
} callback_priorities;

//! regions
typedef enum regions {
    SYSTEM = 0, SDRAM_OUT = 1, SDRAM_IN = 2
} regions;

//! sdram struct
typedef struct sdram_region_t {
    //! base address
    address_t base_address;
    //! size
    uint32_t size;
} sdram_region_t;

//! sdram struct
typedef struct sdram_regions_t {
    //! base address
    uint32_t n_regions;

    //! Entries in the table
    sdram_region_t regions [];
} sdram_regions_t;

//! The number of regions that are to be used for recording
#define NUMBER_OF_REGIONS_TO_RECORD 4

// Globals

sdram_regions_t *out_data;

sdram_regions_t *in_data;

//! The current timer tick value.
// the timer tick callback returning the same value.
uint32_t time;

//! timer tick period (in microseconds)
static uint32_t timer_period;

//! The number of timer ticks to run for before being expected to exit
static uint32_t simulation_ticks = 0;

//! Determines if this model should run for infinite time
static uint32_t infinite_run;

//! read counter
static uint32_t reads = 0;

//! \brief Initialises the model by reading in the regions and checking
//!        recording data.
//! \return True if it successfully initialised, false otherwise
static bool initialise(void) {
    log_debug("Initialise: started");

    // Get the address this core's DTCM data starts at from SRAM
    data_specification_metadata_t *ds_regions =
            data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(ds_regions)) {
        return false;
    }

    // Get the timing details and set up the simulation interface
    if (!simulation_initialise(
            data_specification_get_region(SYSTEM, ds_regions),
            APPLICATION_NAME_HASH, &timer_period, &simulation_ticks,
            &infinite_run, &time, SDP, DMA)) {
        return false;
    }

    // HANDLE SDRAM EDGE STUFF
    out_data = (sdram_regions_t*) data_specification_get_region(
        SDRAM_OUT, ds_regions);
    in_data = (sdram_regions_t*) data_specification_get_region(
        SDRAM_IN, ds_regions);

    // init the sdram to zeros
    for (uint32_t region_id = 0; region_id < out_data->n_regions;
            region_id++) {
        for (uint32_t words_index = 0;
                words_index < (uint32_t) out_data->regions[region_id].size / 4;
                words_index++) {
            out_data->regions[region_id].base_address[words_index] = 0;
        }
    }

    log_debug("Initialise: finished");
    return true;
}

//! \brief the function to call when resuming a simulation
void resume_callback(void) {
}

//! \brief Timer interrupt callback
//! \param[in] timer_count: the number of times this call back has been
//!            executed since start of simulation
//! \param[in] unused: unused parameter kept for API consistency
void timer_callback(UNUSED uint timer_count, UNUSED uint unused) {
    time++;
    log_debug("Timer tick %u \n", time);

    /* if a fixed number of simulation ticks that were specified at startup
     * then do reporting for finishing */
    if (infinite_run != TRUE && time >= simulation_ticks) {

        // Enter pause and resume state to avoid another tick
        simulation_handle_pause_resume(resume_callback);

        log_debug("Completed a run");

        // Subtract 1 from the time so this tick gets done again on the next
        // run
        time--;

        simulation_ready_to_read();
        return;
    }

    // if odd. add 1 to all out regions. else read ins and check count matches
    if (time % 2 == 0) {
        for (uint32_t region_id = 0; region_id < out_data->n_regions;
                region_id++) {
            for (uint32_t words_index = 0;
                    words_index < (uint32_t)
                        out_data->regions[region_id].size / 4;
                    words_index++) {
                out_data->regions[region_id].base_address[words_index] += 1;
            }
        }
        log_info("incremented all regions");
    }
    else {
        reads += 1;
        bool fails = false;
        for (uint32_t region_id = 0; region_id < in_data->n_regions;
                region_id++) {
            for (uint32_t words_index = 0;
                    words_index < (uint32_t)
                        in_data->regions[region_id].size / 4;
                    words_index++) {
                if (in_data->regions[region_id].base_address[
                        words_index] != reads) {
                    log_info(
                        "in region %d has %d instead of %d. BOOM!",
                        region_id,
                        in_data->regions[region_id].base_address[words_index],
                        reads);
                    fails = true;
                }
            }
        }
        if (fails) {
            rt_error(RTE_SWERR);
        }
        log_info("all regions were correct number");
    }
}

//! \brief The entry point for this model.
void c_main(void) {

    // initialise the model
    if (!initialise()) {
        rt_error(RTE_API);
    }

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    // Set timer tick (in microseconds)
    log_debug("setting timer tick callback for %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // Set up the timer tick callback (others are handled elsewhere)
    spin1_callback_on(TIMER_TICK, timer_callback, TIMER);

    simulation_run();
}
