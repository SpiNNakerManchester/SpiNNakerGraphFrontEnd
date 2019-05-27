
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>


uint my_key;
// KA : set parameters that will be used in the receive data method
static circular_buffer input_buffer;
// KA : Transmitted flag
uint32_t flag = 0;


static uint32_t time = 0;

// value for turning on and off interrupts
uint cpsr = 0;

//! The recording flags
static uint32_t recording_flags = 0;

typedef enum regions_e {
    TRANSMISSIONS,
    INPUT,
    RECORDED_DATA
} regions_e;


typedef enum callback_priorities{
    USER = 3
} callback_priorities;


//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;


void send_value(uint data){
    log_info("send_value\n", my_key);
    // send my new state to the simulation neighbours
    log_debug("sending value via multicast with key %d",
              my_key);
    while (!spin1_send_mc_packet(my_key, data, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

    log_debug("sent value 1 via multicast");
}


void record_data(int data) {
    log_info("Recording data\n");
    log_info("data %d",data);


    uint chip = spin1_get_chip_id(); //KA:This function returns the chip ID

    uint core = spin1_get_core_id(); //KA:This function returns the core ID

    log_debug("Issuing 'Const' from chip %d, core %d", chip, core);

    bool recorded = recording_record(0, &data, 4); //KA:Add const value to the SDRAM

    if (recorded) {
        log_debug("Const recorded successfully!");
    } else {
        log_error("Const was not recorded...");
    }
}


//! \brief Initialises the recording parts of the model
//! \return True if recording initialisation is successful, false otherwise
static bool initialise_recording(){
    log_info("initialise_recording\n");
    address_t address = data_specification_get_data_address();
    address_t recording_region = data_specification_get_region(
        RECORDED_DATA, address);
    log_info("recording_region address  is %u\n", recording_region);

    bool success = recording_initialize(recording_region, &recording_flags);
    log_info("Recording flags = 0x%08x", recording_flags);
    return success;
}

void resume_callback() {
    time = UINT32_MAX;
}



void read_input_buffer(){
    log_info("read_input_buffer\n");

    cpsr = spin1_int_disable();
    circular_buffer_print_buffer(input_buffer);
    // pull payloads from input_buffer. Filter for alive and dead states

    log_debug("read_input_buffer");
    spin1_mode_restore(cpsr);
}

/****f*
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void update ()
 *
 * SOURCE
 */
void update() {
    log_info("update\n");

        send_value(1);
        record_data(1);

}


static bool initialize() {
    log_info("Initialise const: started\n");

    // Get the address this core's DTCM data starts at from SDRAM
    address_t address = data_specification_get_data_address();
    log_info("address is %u\n", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    log_info("transmission_region_address  is %u\n", transmission_region_address);
    if (transmission_region_address[HAS_KEY] == 1) { // a pointer to uint32 and if the first element of this array exists so has key do the code bellow
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    } else {
        log_error(
            "cannot find the keys in the regions\n");
        return false;
    }

    // read my const value
    int const_value = data_specification_get_region(
        INPUT, address);
    log_info("my const value is %d\n", const_value);

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
    log_info("starting Tensor const \n");

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

    // kick-start the process
    spin1_schedule_callback(update, 0, 0, USER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
