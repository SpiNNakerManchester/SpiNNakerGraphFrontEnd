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

//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>

//! Provenance data store
typedef struct sdram_block {
    address_t sdram_address;
    uint32_t total_size;
} sdram_block;

//! Provenance data store
typedef struct sdram_blocks {
    uint32_t n_sdram_partitions;
    sdram_block blocks [];
} sdram_blocks;


//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! The recording flags
static uint32_t recording_flags = 0;

//! the SDRAM base address in the
sdram_blocks *constant;
sdram_blocks *segmented;
sdram_blocks *source_segmented;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    BACON = 4,
    SEG_BACON = 5,
    SOURCE_SEG_BACON = 6
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities {
    SDP = 0,
    DMA = 1,
    TIMER = 2,
    USER = 3
} callback_priorities;

static void resume_callback(void) {
    time = UINT32_MAX;
}

#define MAGIC_CONSTANT 4
#define BYTES_TO_WORD_MULTIPLIER 4


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
        simulation_handle_pause_resume(resume_callback);

        if (recording_flags > 0) {
            log_info("updating recording regions");
            recording_finalise();
        }

        // switch to state where host is ready to read
        simulation_ready_to_read();

        return;
    }

    if (time == 15) {
        for (uint32_t constant_sdram_id = 0;
                constant_sdram_id < constant->n_sdram_partitions;
                constant_sdram_id ++){
            uint32_t words = (
                constant->blocks[constant_sdram_id].total_size /
                BYTES_TO_WORD_MULTIPLIER);
            for (uint32_t word_id = 0; word_id < words; word_id ++) {
                constant->blocks[constant_sdram_id].sdram_address[word_id] = (
                    constant->blocks[constant_sdram_id].sdram_address[
                        word_id] * MAGIC_CONSTANT);
            }
        }

        for (uint32_t segmented_sdram_id = 0;
                segmented_sdram_id < segmented->n_sdram_partitions;
                segmented_sdram_id ++) {
            uint32_t words = (
                segmented->blocks[segmented_sdram_id].total_size /
                BYTES_TO_WORD_MULTIPLIER);
            for (uint32_t word_id = 0; word_id < words; word_id ++){
                segmented->blocks[segmented_sdram_id].sdram_address[word_id] = (
                    segmented->blocks[segmented_sdram_id].sdram_address[
                        word_id] * MAGIC_CONSTANT);
            }
        }
    }

    if(time == 25) {
        for (uint32_t src_segmented_sdram_id = 0;
                src_segmented_sdram_id < source_segmented->n_sdram_partitions;
                src_segmented_sdram_id ++) {
            uint32_t words = (
                segmented->blocks[src_segmented_sdram_id].total_size /
                BYTES_TO_WORD_MULTIPLIER);
            for (uint32_t word_id = 0; word_id < words; word_id ++){
                source_segmented->blocks[src_segmented_sdram_id].sdram_address[
                    word_id] = (source_segmented->blocks[
                        src_segmented_sdram_id].sdram_address[word_id] *
                            MAGIC_CONSTANT);
            }
        }
    }

    for (uint32_t constant_sdram_id = 0;
            constant_sdram_id < constant->n_sdram_partitions;
            constant_sdram_id ++) {
        uint32_t words = (
            constant->blocks[constant_sdram_id].total_size /
            BYTES_TO_WORD_MULTIPLIER);
        for (uint32_t word_id = 0; word_id < words; word_id ++) {
            log_info(
                "data in constant sdram region %d for word %d, is %d",
                constant_sdram_id, word_id,
                constant->blocks[constant_sdram_id].sdram_address[word_id]);
        }
    }

    for (uint32_t seg_sdram_id = 0;
            seg_sdram_id < source_segmented->n_sdram_partitions;
            seg_sdram_id ++) {
        uint32_t words = (
            source_segmented->blocks[seg_sdram_id].total_size /
            BYTES_TO_WORD_MULTIPLIER);
        for (uint32_t word_id = 0; word_id < words; word_id ++) {
            log_info(
                "data in source_segmented sdram region %d for word %d, is %d",
                seg_sdram_id, word_id,
                source_segmented->blocks[seg_sdram_id].sdram_address[word_id]);
        }
    }

    for (uint32_t seg_sdram_id = 0;
            seg_sdram_id < segmented->n_sdram_partitions; seg_sdram_id ++) {
        uint32_t words = (
            segmented->blocks[seg_sdram_id].total_size /
            BYTES_TO_WORD_MULTIPLIER);
        for (uint32_t word_id = 0; word_id < words; word_id ++) {
            log_info(
                "data in segmented sdram region %d for word %d, is %d",
                seg_sdram_id, word_id,
                segmented->blocks[seg_sdram_id].sdram_address[word_id]);
        }
    }
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

    constant = data_specification_get_region(BACON, data);
    segmented = data_specification_get_region(SEG_BACON, data);
    source_segmented = data_specification_get_region(SOURCE_SEG_BACON, data);

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
    log_info("starting bacon dest\n");

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
