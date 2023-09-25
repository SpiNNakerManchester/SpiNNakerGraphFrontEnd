/*
 * Copyright (c) 2023 The University of Manchester
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

//! imports
#include <spin1_api.h>
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! The key to send data with
static uint32_t send_key;

//! Whether the data should be sent
static uint32_t do_send;

//! The mask to apply to the key to extract any data before sending
static uint32_t key_mask;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    KEY_DATA_REGION,
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities {
    MC_PACKET = -1,
    SDP = 0,
    DMA = 1,
    TIMER = 2,
    USER = 3
} callback_priorities;

// -------------------------------------------------------------------

static void receive_data_pl(uint key, uint payload) {
    log_info("Key=%u Payload=%u", key, payload);
    if (do_send) {
        uint key_to_send = send_key | (key & key_mask);
        spin1_send_mc_packet(key_to_send, payload, 1);
    }
}

static void receive_data(uint key, UNUSED uint unused) {
    log_info("Key=%u", key);
    if (do_send) {
        uint key_to_send = send_key | (key & key_mask);
        spin1_send_mc_packet(key_to_send, 0, 0);
    }
}

static void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {

        // fall into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        // switch to state where host is ready to read
        simulation_ready_to_read();

        return;
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

    // Get key data
    uint *key_data = data_specification_get_region(KEY_DATA_REGION, data);
    do_send = key_data[0];
    send_key = key_data[1];
    key_mask = key_data[2];

    if (do_send) {
        log_info("Re-sending received keys with key 0x%08x and mask 0x%08x",
                send_key, key_mask);
    } else {
        log_info("Not re-sending received keys");
    }

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

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data_pl, MC_PACKET);
    spin1_callback_on(MC_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
