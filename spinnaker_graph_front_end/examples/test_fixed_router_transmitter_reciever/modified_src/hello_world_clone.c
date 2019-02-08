// DO NOT EDIT! THIS FILE WAS GENERATED FROM src/hello_world_clone.c

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
typedef enum callback_priorities{
    MC_PACKET = -1, SDP = 0, USER = 3, TIMER = 2, DMA = 1
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;



void receive_data(uint key, uint payload) {
    log_mini_info("%u%d%d", 18001, key, payload);
    /* "received fixed route packet with key %d, payload %d"*/
}

void iobuf_data(){
    address_t address = data_specification_get_data_address();
    address_t hello_world_address =
        data_specification_get_region(RECORDED_DATA, address);

    log_mini_info("%u%08x", 18002, hello_world_address);  /* "Hello world address is %08x"*/

    char* my_string = (char *) &hello_world_address[1];
    log_mini_info("%u%s", 18003, my_string);  /* "Data read is: %s"*/
}

void record_data() {
    log_mini_debug("%u", 18004);  /* "Recording data..."*/

    uint chip = spin1_get_chip_id();

    uint core = spin1_get_core_id();

    log_mini_debug("%u%d%d", 18005, chip, core);  /* "Issuing 'Hello World' from chip %d, core %d"*/

    bool recorded = recording_record(
        0, "Hello world", 11 * sizeof(char));

    if (recorded) {
        log_mini_debug("%u", 18006);  /* "Hello World recorded successfully!"*/
    } else {
        log_mini_error("%u", 18007);  /* "Hello World was not recorded..."*/
    }
}


//! \brief Initialises the recording parts of the model
//! \return True if recording initialisation is successful, false otherwise
static bool initialise_recording(){
    address_t address = data_specification_get_data_address();
    address_t recording_region = data_specification_get_region(
        RECORDED_DATA, address);

    bool success = recording_initialize(recording_region, &recording_flags);
    log_mini_info("%u%08x", 18008, recording_flags);  /* "Recording flags = 0x%08x"*/
    return success;
}

void resume_callback() {
    time = UINT32_MAX;
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
void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    log_mini_debug("%u%d%d", 18009, time, simulation_ticks);  /* "on tick %d of %d"*/

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        log_mini_info("%u", 18010);  /* "Simulation complete.\n"*/

        if (recording_flags > 0) {
            log_mini_info("%u", 18011);  /* "updating recording regions"*/
            recording_finalise();
        }

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(resume_callback);

        return;

    }

    if (time == 1) {
        record_data();
    } else if (time ==  100) {
        iobuf_data();
    }

    // trigger buffering_out_mechanism
    log_mini_info("%u%d", 18012, recording_flags);  /* "recording flags is %d"*/
    if (recording_flags > 0) {
        log_mini_info("%u", 18013);  /* "doing timer tick update\n"*/
        recording_do_timestep_update(time);
        log_mini_info("%u", 18014);  /* "done timer tick update\n"*/
    }
}

static bool initialize(uint32_t *timer_period) {
    log_mini_info("%u", 18015);  /* "Initialise: started\n"*/

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        log_mini_error("%u", 18016);  /* "failed to read the data spec header"*/
        return false;
    }

    // Get the timing details and set up the simulation interface
    if (!simulation_initialise(
            data_specification_get_region(SYSTEM_REGION, address),
            APPLICATION_NAME_HASH, timer_period, &simulation_ticks,
            &infinite_run, SDP, DMA)) {
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
void c_main() {
    log_mini_info("%u", 18017);  /* "starting heat_demo\n"*/

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // initialise the recording section
    // set up recording data structures
    if(!initialise_recording()){
         rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_mini_info("%u%d", 18018, timer_period);  /* "setting timer to execute every %d microseconds"*/
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(FR_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(FRPL_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_mini_info("%u", 18019);  /* "Starting\n"*/

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
