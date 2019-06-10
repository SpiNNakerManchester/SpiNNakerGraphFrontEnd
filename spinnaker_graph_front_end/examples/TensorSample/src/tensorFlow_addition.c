
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>

int value_a;
int value_b;
int counter = 0;
int result = 0;

uint my_key;
// KA : set parameters that will be used in the receive data method
static circular_buffer input_buffer;
// KA : Transmitted flag
uint32_t flag = 0;

address_t address = NULL;

typedef enum regions_e {
    INPUT_CONST_VALUES,
    RECORDED_DATA
} regions_e;


typedef enum callback_priorities{
    MC_PACKET = -1, USER = 3
} callback_priorities;


void record_data(int result) {
    log_info("Recording data\n");

    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    spin1_memcpy(record_space_address, &result, 4);
    log_info("recorded result %d\n", result);

}

int addition(int a, int b){
    log_info("addition\n");
    int total;
    log_info("Addition of A %d and B %d \n", a , b);
    total = a + b;
    log_info("Addition Result : %d \n", total);
    return total;
}


void receive_data(uint key, uint payload) {
    log_info("receive_data\n");
    log_info("the key i've received is %d\n", key);
    log_info("the payload i've received is %d\n", payload);
    counter +=1;
    if(counter == 1){
        value_a = payload;
    }
    else{
        value_b = payload;
        result = addition(value_a, value_b);
        record_data(result);
        spin1_exit(0);
    }
}

static bool initialize() {
    log_info("Initialise addition: started\n");

    // Get the address this core's DTCM data starts at from SDRAM
    address_t address = data_specification_get_data_address();
    log_info("address is %u\n", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(256);
    if (input_buffer == 0){
        return false;
    }
    log_info("input_buffer initialised");

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
    log_info("starting Tensor addition\n");

    // initialise the model
    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    log_info("Starting\n");

spin1_start(SYNC_WAIT);
}
