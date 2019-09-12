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

#define REAL_CONST(x)	x##k		// accum -> k
#define UREAL_CONST(x)	x##uk		// unsigned accum -> uk
#define FRACT_CONST(x)	x##lr
#define UFRACT_CONST(x)	x##ulr

//! imports
#include "spin1_api.h"
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

//! The recording flags
static uint32_t recording_flags = 0;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    RECORDED_DATA
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

static void receive_data(uint key, uint payload) {
    use(key);
    use(payload);
}

static void iobuf_data(void) {
    data_specification_metadata_t *data = data_specification_get_data_address();
    address_t hello_world_address =
	    data_specification_get_region(RECORDED_DATA, data);

    log_debug("logger_example address is %08x", hello_world_address);

    char* my_string = (char *) &hello_world_address[1];
    log_debug("Data read is: %s", my_string);
}

static void record_data(void) {
    log_debug("Recording data...");

    uint chip = spin1_get_chip_id();
    uint core = spin1_get_core_id();

    log_debug("Issuing 'Hello World' from chip %d, core %d", chip, core);

    bool recorded = recording_record(
	    0, "Hello world", 11 * sizeof(char));

    if (recorded) {
        log_debug("Hello World recorded successfully!");
    } else {
        log_error("Hello World was not recorded...");
    }
}

//! \brief Initialises the recording parts of the model
//! \return True if recording initialisation is successful, false otherwise
static bool initialise_recording(void) {
    data_specification_metadata_t *data = data_specification_get_data_address();
    address_t recording_region =
	    data_specification_get_region(RECORDED_DATA, data);

    bool success = recording_initialize(recording_region, &recording_flags);
    log_debug("Recording flags = 0x%08x", recording_flags);
    return success;
}

static void resume_callback(void) {
    time = UINT32_MAX;
}

static uint32_t calc_sum(uint32_t a, uint32_t b){
    return a + b;
}

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
        log_debug("Simulation complete.");

        // fall into the pause resume mode of operating
        simulation_handle_pause_resume(resume_callback);

        if (recording_flags > 0) {
            log_debug("updating recording regions");
            recording_finalise();
        }

        log_info("Starting log examples");
        log_info("Float 1.0f as Hex: 3f800000 == %a", 1.0f);
        log_info("Double 1.0f as Hex: 3ff0000000000000 == %A", 1.0d);
        log_info("Char: q == %c", 'q');
        log_info("Signed Decimal: 12345 = %d", 12345);
        log_info("Signed Decimal: 1 = %d", 1);
        log_info("Signed Decimal: 0 = %d", 0);
        log_info("Signed Decimal: -1 = %d", -1);
        log_info("Signed Decimal: -13579 = %d", -13579);
        log_info("Signed Decimal (using i): 100 = %i", 100);
        log_info("Float: 21213433434.342134342 ~ %f", 21213433434.342134342f);
        log_info("Float: 1.0 = %f", 1.0f);
        log_info("Float: 0.000000000000043343 ~ %f", 0.000000000000043343f);
        log_info("Float: 0.0 = %f", 0.0f);
        log_info("Float: -0.000000000000043343 ~ %f", -0.000000000000043343f);
        log_info("Float: -2.0 = %f", -2.0f);
        log_info("Float: -434345454545522.453534 ~ %f", -434345454545522.453534f);
        log_info("Float: 1/0 = %f", 1/0.0f);
        log_info("Float: 0/0 = %f", 0/0.0f);
        log_info("Float: -1/0 = %f", -1/0.0f);
        log_info("Double: 21213433434.342134342 ~ %F", 21213433434.342134342d);
        log_info("Double: 1.0 = %F", 1.0d);
        log_info("Double: 0.000000000000043343 ~ %F", 0.000000000000043343d);
        log_info("Double: 0.0 = %F", 0.0d);
        log_info("Double: -0.000000000000043343 ~ %F", -0.000000000000043343d);
        log_info("Double: -2.0 = %F", -2.0d);
        log_info("Double: -434345454545522.453534 ~ %F", -434345454545522.453534f);
        log_info("Double: 1/0 = %d", 1/0.0d);
        log_info("Double: 0/0 = %d", 0/0.0d);
        log_info("Double: -1/0 = %d", -1/0.0d);
        log_info("ISO signed accum: 12.34 = %k", REAL_CONST(12.34));
        log_info("ISO signed accum: -44312.3344 = %k", REAL_CONST(-44312.3344));
        log_info("ISO signed accum: 0 = %k", REAL_CONST(0.0));
        log_info("ISO unsigned accum: 3245.33 = %K", UREAL_CONST(3245.33));
        log_info("ISO unsigned accum: 55545.4334 = %K", UREAL_CONST(55545.4334));
        log_info("ISO unsigned accum: 0 = %K", UREAL_CONST(0.0));
        log_info("ISO signed fract: 0.9873 = %r", FRACT_CONST(0.9873));
        log_info("ISO signed fract: 0 = %r", FRACT_CONST(0.0));
        log_info("ISO unsigned fract: 0.9873 = %R", FRACT_CONST(0.9873));
        log_info("ISO unsigned fract: 0 = %R", FRACT_CONST(0.0));
        log_info("Unsigned Decimal: 12345 = %u", 12345);
        log_info("Unsigned Decimal: 1 = %u", 1);
        log_info("unsigned Decimal: 0 = %u", 0);
        log_info("Hex Decimal: 1 = %x", 1);
        log_info("Hex Decimal: 0 = %x", 0);
        log_info("Function params 1+2 = %i 3+4 = %d", calc_sum(1,2), calc_sum(3,4));
        log_info("Done log examples");

        // switch to state where host is ready to read
        simulation_ready_to_read();

        return;
    }

    if (time == 1) {
        record_data();
    } else if (time ==  100) {
        iobuf_data();
    }

    // trigger buffering_out_mechanism
    log_debug("recording flags is %d", recording_flags);
    if (recording_flags > 0) {
        log_debug("doing timer tick update");
        recording_do_timestep_update(time);
        log_debug("done timer tick update");
    }
}

static bool initialize(uint32_t *timer_period) {
    log_debug("Initialise: started\n");

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
    log_info("starting logger demo\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // initialise the recording section
    // set up recording data structures
    if (!initialise_recording()) {
         rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_debug("setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_debug("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
