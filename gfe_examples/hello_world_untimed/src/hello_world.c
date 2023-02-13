/*
 * Copyright (c) 2017-2023 The University of Manchester
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

//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>

//! Where we are and where to go in the simulation
static uint32_t step = 0;
static uint32_t n_steps = 0;
static uint32_t run_forever = 0;

//! The recording flags
static uint32_t recording_flags = 0;

//! The data
typedef struct char_data {
    uint32_t n_chars;
    uint8_t chars[];
} char_data;
static char_data *c_data;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    PARAMS_REGION,
    RECORDED_DATA
} regions_e;


//! values for the priority for each callback
typedef enum callback_priorities {
    SDP = 0,
    DMA = 1
} callback_priorities;

// -------------------------------------------------------------------

static void record_data(void) {
    bool recorded = recording_record(0, c_data->chars, c_data->n_chars * sizeof(char));
    if (!recorded) {
        log_error("Data was not recorded...");
    }
}


//! \brief Initialises the recording parts of the model
//! \return True if recording initialisation is successful, false otherwise
static bool initialise_recording(void) {
    data_specification_metadata_t *data = data_specification_get_data_address();
    void *recording_region = data_specification_get_region(RECORDED_DATA, data);
    bool success = recording_initialize(&recording_region, &recording_flags);
    return success;
}

static void resume_callback(void);

static void run(uint unused0, uint unused1) {
    use(unused0);
    use(unused1);

    // Increment the step as it will start at "-1"
    step++;

    log_info("Running from step %u until %u", step, n_steps);
    while (run_forever || step < n_steps) {
        if (recording_flags) {
            record_data();
        }
        step++;
    }

    log_info("Steps run");
    simulation_handle_pause_resume(resume_callback);
    if (recording_flags) {
        recording_finalise();
    }
    log_info("Making ready...");
    simulation_ready_to_read();
    log_info("Done");
}

// ! \brief Called when simulation is about to restart
static void resume_callback(void) {
    recording_reset();
    log_info("Scheduling callback from resume");
    spin1_schedule_callback(run, 0, 0, 1);
}


static void exit_callback(void) {
    if (recording_flags) {
        recording_finalise();
    }
}

static void start_callback(void) {
    log_info("Scheduling callback from start");
    spin1_schedule_callback(run, 0, 0, 1);
}

static bool initialize(void) {
    // Get the address this core's DTCM data starts at from SRAM
    data_specification_metadata_t *data = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(data)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // set up the simulation interface
    if (!simulation_steps_initialise(
            data_specification_get_region(SYSTEM_REGION, data),
            APPLICATION_NAME_HASH, &n_steps, &run_forever, &step, SDP, DMA)) {
        return false;
    }

    char_data *sdram_data = data_specification_get_region(PARAMS_REGION, data);
    uint32_t size = sizeof(char_data) + (sdram_data->n_chars * sizeof(uint8_t));
    c_data = spin1_malloc(size);
    if (c_data == NULL) {
        log_error("Failed to allocate local data");
        return false;
    }
    spin1_memcpy(c_data, sdram_data, size);
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
    // initialise the model
    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // initialise the recording section
    // set up recording data structures
    if (!initialise_recording()) {
         rt_error(RTE_SWERR);
    }

    simulation_set_exit_function(exit_callback);
    simulation_set_start_function(start_callback);
    simulation_set_uses_timer(false);
    simulation_run();
}
