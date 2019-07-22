//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>


uint my_key;

int scalar = 0;

address_t address = NULL;

typedef enum regions_e {
    TRANSMISSIONS,
    RECORDED_DATA
} regions_e;


typedef enum callback_priorities{
    MC_PACKET = -1, USER = 3
} callback_priorities;


typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;


void send_value(){
    log_info("send_value\n", scalar);

    log_info("sending value via multicast with key %d",
              my_key);
    while (!spin1_send_mc_packet(my_key, scalar, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

}


void record_data(){
    //* record const value in SDRAM
    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    spin1_memcpy(record_space_address, &scalar, 4);
    log_debug("recorded my scalar  \n");
}


void apply_neg_sign(){
    log_info("apply_neg_sign\n");

    scalar = scalar * (-1);

    log_info("%d\n", scalar);
}


void receive_data(uint key, uint payload) {
    log_info("key %d , data %d\n", key, payload);

        scalar = payload;
        log_info("V1:key %d ,V1:scalar value %d\n", key, scalar);
        apply_neg_sign();
        send_value();
        record_data();
        spin1_exit(0);
}


static bool initialize() {
    log_info("Initialise neg: started\n");

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
    // a pointer to uint32 and if the first element of this array exists so has key do the code bellow
    if (transmission_region_address[HAS_KEY] == 1) {
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    } 
    else {
        log_error(
            "cannot find the keys in the regions\n");
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
    log_info("starting Tensor const \n");

    // initialise the model
    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    // start execution
    log_info("Starting\n");

spin1_start(SYNC_WAIT);

}