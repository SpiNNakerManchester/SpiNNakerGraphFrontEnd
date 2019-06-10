
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>


uint my_key;

// KA : Transmitted flag
uint32_t flag = 0;

uint32_t const_value=0;

static uint32_t time = 0;

address_t address = NULL;

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


typedef enum initial_input_region_elements {
    INITIAL_INPUT
} initial_state_region_elements;

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


void record_data(){
    //* record const value in sdram
    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    spin1_memcpy(record_space_address, &const_value, 4);
    log_debug("recorded my const_valuet \n");
}


void resume_callback() {
    time = UINT32_MAX;
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

        send_value(const_value);
        record_data(const_value);
        spin1_exit(0);

}


static bool initialize() {
    log_info("Initialise const: started\n");

    // Get the address this core's DTCM data starts at from SDRAM
    address = data_specification_get_data_address();
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
    address_t my_input_region_address = data_specification_get_region(
        INPUT, address);
    const_value = my_input_region_address[INITIAL_INPUT];
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

    // initialise the model
    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // kick-start the process
    spin1_schedule_callback(update, 0, 0, USER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

spin1_start(SYNC_WAIT);

}
