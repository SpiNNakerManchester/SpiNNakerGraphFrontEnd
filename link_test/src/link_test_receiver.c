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

#define N_LINKS 6

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

typedef struct {

    // Keys to expect from neighbours
    uint32_t receive_keys[N_LINKS];

    // Masks to expect from neighbours
    uint32_t receive_masks[N_LINKS];

    // The number of packets received considered OK (calculated on host)
    uint32_t packet_count_ok;

    // Whether to write the routes
    uint32_t write_routes;
} config_data_t;

typedef struct {
    // Flags for links on which the packet count is considered "OK"
    uint32_t links_count_ok;

    // Flags for links on which the failure number is considered "OK"
    uint32_t links_fails_ok;

    // Flags for links which are available from SCAMP
    uint32_t known_links;

    // Count of unknown keys
    uint32_t unknown_keys;
} provenance_data_t;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    CONFIG_REGION,
    PROVENANCE_REGION
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities {
    MC_PACKET = -1,
    SDP = 0,
    TIMER = 0,
    DMA = 1
} callback_priorities;

// The change in x when going over each link
static const int32_t LINK_DELTA_X[] = {1, 1, 0, -1, -1, 0};

// The change in y when going over each link
static const int32_t LINK_DELTA_Y[] = {0, 1, 1, 0, -1, -1};

// The configuration
static config_data_t config;

// Counts of packets received
static uint32_t packets_received[N_LINKS];

// Counts of "Incorrect data" in packets received
static uint32_t fails_received[N_LINKS];

// Expected data from adjacent chips, based on sv data for this chip
static uint32_t expected_data[N_LINKS];

// The number of unknown keys received
static uint32_t unknown_keys = 0;

// -------------------------------------------------------------------

static void receive_data(uint key, uint payload) {
    uint32_t key_found = 0;
    for (uint32_t i = 0; i < N_LINKS; i++) {
        if ((key & config.receive_masks[i]) == config.receive_keys[i]) {
            packets_received[i]++;
            if (payload != expected_data[i]) {
                fails_received[i]++;
            }
            key_found = 1;
            break;
        }
    }
    if (!key_found) {
        unknown_keys++;
    }
}

//! \brief Writes the provenance data
//! \param[out] provenance_region: Where to write the provenance
static void store_provenance_data(address_t provenance_region) {
    provenance_data_t *prov = (void *) provenance_region;

    uint32_t links_ok = 0;
    uint32_t fails_ok = 0;
    for (uint32_t i = 0; i < N_LINKS; i++) {
        log_info("Link %u: packets received %u, packets failed %u, ok %u",
                i, packets_received[i], fails_received[i], config.packet_count_ok);
        if (packets_received[i] >= config.packet_count_ok) {
            links_ok |= (1 << i);
        }
        if (fails_received[i] == 0) {
            fails_ok |= (1 << i);
        }
    }

    // store the data into the provenance data region
    prov->known_links = sv->link_en;
    prov->links_count_ok = links_ok;
    prov->links_fails_ok = fails_ok;
    prov->unknown_keys = unknown_keys;
}

/****f*
 *
 * SUMMARY
 *send_data
 * SYNOPSIS
 *  void update (uint ticks, uint b)
 *
 * SOURCE
 */
static void timer(UNUSED uint a, UNUSED uint b) {
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
}

static inline uint32_t get_next(uint32_t value, uint32_t max, int32_t delta) {
    int32_t result = value + delta;
    if (result < 0) {
        return max - 1;
    }
    uint32_t u_result = (uint32_t) result;
    if (u_result >= max) {
        return 0;
    }
    return u_result;
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

    simulation_set_provenance_function(
            store_provenance_data,
            data_specification_get_region(PROVENANCE_REGION, data));

    // Read the config data
    config_data_t *sdram_data = data_specification_get_region(CONFIG_REGION, data);
    config = *sdram_data;

    // Set up the link data to send
    p2p_data_t core_data;
    core_data.p2p_addr = sv->p2p_addr;
    core_data.p2p_dims = sv->p2p_dims;

    // Set up the link data expected (from adjacent links)
    for (uint32_t i = 0; i < N_LINKS; i++) {
        p2p_data_t link_data = core_data;
        link_data.x = get_next(core_data.x, core_data.x_size, LINK_DELTA_X[i]);
        link_data.y = get_next(core_data.y, core_data.y_size, LINK_DELTA_Y[i]);
        expected_data[i] = link_data.data;
    }

    // Set up routes
    if (config.write_routes) {
        uint route = 1 << (spin1_get_core_id() + N_LINKS);
        uint e = rtr_alloc(N_LINKS);
        for (uint32_t i = 0; i < N_LINKS; i++) {
            rtr_mc_set(e + i, config.receive_keys[i], config.receive_masks[i],
                    route);
        }
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
    log_info("starting link receiver\n");

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
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(TIMER_TICK, timer, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
