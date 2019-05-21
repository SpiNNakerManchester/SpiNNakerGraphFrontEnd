
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <recording.h>
#include <debug.h>

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! The recording flags
static uint32_t recording_flags = 0;
static bool initialise_recording();

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    TRANSMISSIONS,
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

// TODO: Update with the number of recorded regions
#define N_REGIONS_TO_RECORD 1

// TODO: Set the application name here
static char *app_name = "";

// The Key
static uint32_t my_key;


//=============================================================================
// packet interfaces


//! \brief functionality to add when received a multicast packet without
//         payload.
//! \param[in] key is the key used in routing
//! \param[in] payload is the payload of packet [none].
//! \return None
void receive_data_no_payload(uint key, uint payload) {
    use(payload);

    // TODO: Handle a received multicast packet without a payload
}

//! \brief functionality to add when received a multicast packet with payload.
//! \param[in] key is the key used in routing
//! \param[in] payload is the payload of packet.
//! \return None
void receive_data_payload(uint key, uint payload) {

    // TODO: Handle a received multicast packet with a payload
}

//! \brief

//=============================================================================
// timer tick interface

//! \brief functionality to execute within a timer tick callback.
//! \param[in] ticks the number of times the timer tick callback has been
//                    called.
//! \param[in] time the tracked timer.
//! \return None
static void do_update(uint ticks, uint32_t time) {

    // TODO: Handle a timer tick

    // TODO: Add any other functionality e.g. recording, iobuf etc.
    //       For further useful functions e.g. recording_record,
    //       recording_do_timestep_update, see other graph_front_end examples

}

//=============================================================================
//resume interfaces

//! \brief add functionality to do when you are about to resume.
void resume_callback() {

    // TODO: Perform any changes that need to be done before resume occurs
    initialise_recording();
}

//==============================================================================
//==============================================================================
//========================= Boiler plate code below ============================
//==============================================================================
//==============================================================================

//! \brief Initialises the recording parts of the model
//! \return True if recording initialisation is successful, false otherwise
static bool initialise_recording() {
    address_t address = data_specification_get_data_address();

    // TODO: Update with the recording region IDs
    address_t regions_addresses_to_record = data_specification_get_region(
            RECORDED_DATA, address);

    bool success = recording_initialize(regions_addresses_to_record,
            &recording_flags);
    log_info("Recording flags = 0x%08x", recording_flags);
    return success;
}

//! \brief timer tick callback functionality
//! \param[in] ticks: the number of timer interrupts received
//! \param[in] unused: unused parameter - ignored
//! \return None
void update(uint ticks, uint unused) {
    use(unused);
    use(ticks);

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

    do_update(ticks, time);

}

//! \brief sets up state variables for the system
//! \param[in] timer_period: pointer to the time between timer tick callbacks
//! \return: bool which states if it succeed or not
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

    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    if (transmission_region_address[HAS_KEY] == 1) {
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    }

    return true;
}

//! \brief main entrance method for the model
//!        Used to register event callbacks and begin the simulation
//! \return None
void c_main() {
    log_info("starting %s\n", app_name);

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
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data_payload, MC_PACKET);
    spin1_callback_on(MC_PACKET_RECEIVED, receive_data_no_payload, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
