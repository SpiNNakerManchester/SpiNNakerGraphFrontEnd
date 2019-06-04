
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
    use(key);
    use(payload);
}

void iobuf_data(){
    address_t address = data_specification_get_data_address();
    address_t hello_world_address =
        data_specification_get_region(RECORDED_DATA, address);

    log_info("Hello world address is %08x", hello_world_address);

    char* my_string = (char *) &hello_world_address[1];
    log_info("Data read is: %s", my_string);
}

void record_data() {
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
static bool initialise_recording(){
    address_t address = data_specification_get_data_address();
    address_t recording_region = data_specification_get_region(
        RECORDED_DATA, address);

    bool success = recording_initialize(recording_region, &recording_flags);
    log_info("Recording flags = 0x%08x", recording_flags);
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

    log_debug("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        log_info("Simulation complete.\n");

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

    if (time == 1) {
        record_data();
    } else if (time ==  100) {
        iobuf_data();
    }

    // trigger buffering_out_mechanism
    log_info("recording flags is %d", recording_flags);
    if (recording_flags > 0) {
        log_info("doing timer tick update\n");
        recording_do_timestep_update(time);
        log_info("done timer tick update\n");
    }
}

static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started\n");

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
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
    log_info("starting heat_demo\n");

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
