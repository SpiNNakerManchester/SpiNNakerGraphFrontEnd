/*
 * Copyright (c) 2016 The University of Manchester
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
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>
#include <recording.h>

/*! multicast routing keys to communicate with neighbours */
uint my_key;

/*! buffer used to store spikes */
static circular_buffer input_buffer;
static uint32_t current_payload;

//! conways specific data items
uint32_t my_state = 0;
int alive_states_recieved_this_tick = 0;
int dead_states_recieved_this_tick = 0;

//! recorded data items
uint32_t size_written = 0;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t time = 0;
data_specification_metadata_t *data = NULL;

//! The recording flags
static uint32_t recording_flags = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

// value for turning on and off interrupts
uint cpsr = 0;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    TRANSMISSIONS,
    STATE,
    NEIGHBOUR_INITIAL_STATES,
    RECORDED_DATA
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities {
    MC_PACKET = -1,
    SDP = 1,
    TIMER = 2,
    DMA = 3
} callback_priorities;

//! values for the states
typedef enum states_values {
    DEAD = 0,
    ALIVE = 1
} states_values;

//! definitions of each element in the transmission region
typedef struct transmission_region {
    uint32_t has_key;
    uint32_t my_key;
} transmission_region_t;

//! definitions of each element in the initial state region
typedef struct state {
    uint32_t initial_state;
} state_t;

//! definitions of each element in the initial neighbour state region
typedef struct neighbour_states {
    uint32_t alive_states;
    uint32_t dead_states;
} neighbour_states_t;


/****f* conways.c/receive_data
 *
 * SUMMARY
 *  This function is used as a callback for packet received events.
 * receives data from 8 neighbours and updates the states params
 *
 * SYNOPSIS
 *  void receive_data (uint key, uint payload)
 *
 * INPUTS
 *   uint key: packet routing key - provided by the RTS
 *   uint payload: packet payload - provided by the RTS
 *
 * SOURCE
 */
void receive_data(uint key, uint payload) {
    use(key);
    //log_info("the key i've received is %d\n", key);
    //log_info("the payload i've received is %d\n", payload);
    // If there was space to add spike to incoming spike queue
    if (!circular_buffer_add(input_buffer, payload)) {
        log_info("Could not add state");
    }
}

void do_safety_check(void) {
    // do a safety check on number of states. Not like we can fix it
    // if we've missed events
    cpsr = spin1_int_disable();
    int total = alive_states_recieved_this_tick +
	    dead_states_recieved_this_tick;
    if (total != 8){
         log_error("didn't receive the correct number of states");
         log_error("only received %d states", total);
    }
    log_debug("only received %d alive states",
	    alive_states_recieved_this_tick);
    log_debug("only received %d dead states",
	    dead_states_recieved_this_tick);
    spin1_mode_restore(cpsr);
}

void read_input_buffer(void) {
    cpsr = spin1_int_disable();
    circular_buffer_print_buffer(input_buffer);

    // pull payloads from input_buffer. Filter for alive and dead states
    for (uint32_t counter = 0; counter < 8; counter++) {
        bool success = circular_buffer_get_next(input_buffer, &current_payload);
        if (success) {
            if (current_payload == DEAD) {
                 dead_states_recieved_this_tick += 1;
            } else if (current_payload == ALIVE) {
                 alive_states_recieved_this_tick += 1;
            } else {
                 log_error("Not recognised payload");
            }
        } else {
            log_debug("couldn't read state from my neighbours.");
        }

    }
    spin1_mode_restore(cpsr);
}

void send_state(void) {
    // reset for next iteration
    alive_states_recieved_this_tick = 0;
    dead_states_recieved_this_tick = 0;

    // send my new state to the simulation neighbours
    log_debug("sending my state of %d via multicast with key %d",
	    my_state, my_key);
    while (!spin1_send_mc_packet(my_key, my_state, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

    log_debug("sent my state via multicast");
}

void next_state(void) {
    // calculate new state from the total received so far
    if (my_state == ALIVE) {
        if (alive_states_recieved_this_tick <= 1) {
            my_state = DEAD;
        }
        if ((alive_states_recieved_this_tick == 2) |
                (alive_states_recieved_this_tick == 3)) {
            my_state = ALIVE;
        }
        if (alive_states_recieved_this_tick >= 4) {
            my_state = DEAD;
        }
    } else if (alive_states_recieved_this_tick == 3) {
        my_state = ALIVE;
    }
}

/****f* conways.c/update
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void update (uint ticks, uint b)
 *
 * SOURCE
 */
void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    log_info("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        // fall into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        // Finalise any recordings that are in progress, writing back the final
        // amounts of samples recorded to SDRAM
        if (recording_flags > 0) {
            log_info("updating recording regions");
            recording_finalise();
        }

        log_info("Simulation complete.");

        // switch to state where host is ready to read
        simulation_ready_to_read();

        return;
    }

    if (time == 0) {
        next_state();
        send_state();
        recording_record(0, &my_state, 4);
        log_debug("Send my first state!");
    } else {
        read_input_buffer();

        // find my next state
        next_state();

        // do a safety check on number of states. Not like we can fix it
        // if we've missed events
        do_safety_check();

        send_state();

        recording_record(0, &my_state, 4);
    }
}

//! \brief this method is to catch strange behaviour
//! \param[in] key: the key being received
//! \param[in] unknown: second arg with no state. set to zero by default
void receive_data_void(uint key, uint unknown) {
    use(key);
    use(unknown);
    log_error("this should never ever be done");
}

static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started");

    // Get the address this core's DTCM data starts at from SRAM
    data = data_specification_get_data_address();

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

    // initialise transmission keys
    transmission_region_t *transmission_sdram =
	    data_specification_get_region(TRANSMISSIONS, data);
    if (!transmission_sdram->has_key) {
        log_error(
        	"this conways cell can't affect anything, deduced as an error,"
        	"please fix the application fabric and try again");
        return false;
    }
    my_key = transmission_sdram->my_key;
    log_info("my key is %d", my_key);

    // read my state
    state_t *state_sdram = data_specification_get_region(STATE, data);
    my_state = state_sdram->initial_state;
    log_info("my initial state is %d", my_state);

    // read neighbour states for initial tick
    neighbour_states_t *neigbhour_state_sdram =
	    data_specification_get_region(NEIGHBOUR_INITIAL_STATES, data);
    alive_states_recieved_this_tick = neigbhour_state_sdram->alive_states;
    dead_states_recieved_this_tick = neigbhour_state_sdram->dead_states;

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(256);
    if (input_buffer == 0) {
        return false;
    }
    log_info("input_buffer initialised");

    void *recording_region = data_specification_get_region(RECORDED_DATA, data);
    bool success = recording_initialize(&recording_region, &recording_flags);
    log_info("Recording flags = 0x%08x", recording_flags);
    return success;
}

/****f* conways.c/c_main
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
    log_info("starting conway_cell");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        log_error("Error in initialisation - exiting!");
        rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_info("setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
