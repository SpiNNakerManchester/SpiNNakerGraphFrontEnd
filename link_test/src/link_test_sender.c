/*
 * Copyright (c) 2023 The University of Manchester
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
#include "link_test.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

typedef struct {
    // Key to send to neighbours with
    uint32_t send_key;

    // Mask to send to neighbours with
    uint32_t send_mask;

    // How many times to send per time step
    uint32_t sends_per_timestep;

    // Time between sends (calculated on host)
    uint32_t time_between_sends_us;

    // Whether or not to write the route
    uint32_t write_route;
} config_data_t;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    CONFIG_REGION
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities {
    SDP = 0,
    TIMER = 0,
    DMA = 1
} callback_priorities;

// The configuration
static config_data_t config;

// The data to send to adjacent chips
static p2p_data_t data_to_send;

// -------------------------------------------------------------------

/****f*
 *
 * SUMMARY
 *send_data
 * SYNOPSIS
 *  void update (uint ticks, uint b)
 *
 * SOURCE
 */
static void send_data(UNUSED uint a, UNUSED uint b) {
    time++;

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        log_info("Testing complete.");

        // fall into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        // switch to state where host is ready to read
        simulation_ready_to_read();

        return;
    }

    for (uint32_t i = 0; i < config.sends_per_timestep; i++) {
        spin1_send_mc_packet(config.send_key + i, data_to_send.data, 1);
        spin1_delay_us(config.time_between_sends_us);
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

    // Read the config data
    config_data_t *sdram_data = data_specification_get_region(CONFIG_REGION, data);
    config = *sdram_data;

    // Set up the link data to send
    data_to_send.p2p_addr = sv->p2p_addr;
    data_to_send.p2p_dims = sv->p2p_dims;

    // Add a route for the sender key
    if (config.write_route) {
        uint e = rtr_alloc(1);
        uint route = sv->link_en;
        rtr_mc_set(e, config.send_key, config.send_mask, route);
    }

    return true;
}

/****f*
 *
 * SUMMARY
 *  This function is called at application start-up.
 *  It is used to register event callbacks and begin the simulation.
 *y_sizey_size
 * SYNOPSIS
 *  int c_main()
 *
 * SOURCEy_size
 */
void c_main(void) {
    log_info("starting heat_demo\n");

    // Load DTCM datan_links
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_info("Setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(TIMER_TICK, send_data, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
