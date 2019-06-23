
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>


uint my_key;

int const_value;
int rank;
int input_size;
uint32_t *shape_addr_dtcm;
uint32_t *input_addr_dtcm;

address_t address = NULL;

typedef enum regions_e {
    TRANSMISSIONS,
    TENSOR_PROPERTIES,
    INPUT,
    RECORDED_DATA
} regions_e;


typedef enum callback_priorities{
    USER = 3
} callback_priorities;


typedef enum initial_input_region_elements {
    INITIAL_INPUT
} initial_state_region_elements;


typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;


void send_value(){
    log_info("send_value method \n");
    log_info("first key %d\n", my_key);

    // send size
    while (!spin1_send_mc_packet(my_key, input_size, WITH_PAYLOAD)) {
       spin1_delay_us(1);
    }

    // send rank and shape

    ++my_key;
    log_info("send rank value %d\n", rank);
    while (!spin1_send_mc_packet(my_key, rank, WITH_PAYLOAD)) {
       spin1_delay_us(1);
   }
        
    if(rank != 0){
        ++my_key;
        for(int i=0; i<rank; i++){
            log_info("send dimension value %d\n", shape_addr_dtcm[i]);
            while (!spin1_send_mc_packet(i+my_key, shape_addr_dtcm[i], WITH_PAYLOAD)) {
                spin1_delay_us(1);
        }
        }
    }
    
    // send tensor values
    ++my_key;
    for(int i=0; i<input_size; i++){
        log_info("send array value %d\n", input_addr_dtcm[i]);
        while (!spin1_send_mc_packet(i+my_key, input_addr_dtcm[i], WITH_PAYLOAD)) {
            spin1_delay_us(1);
        }
    }
}


void record_data(){
    //* record const value in SDRAM
    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    spin1_memcpy(record_space_address, &const_value, 4);
    log_debug("recorded my const_valuet \n");
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

        send_value();
        // record_data();
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
    // a pointer to uint32 and if the first element of this array exists so has key do the code bellow
    if (transmission_region_address[HAS_KEY] == 1) {
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    } 
    // else {
    //     log_error(
    //         "cannot find the keys in the regions\n");
    //     return false;
    // }

    // read my shape
    address_t shape_region_address = data_specification_get_region(TENSOR_PROPERTIES, address);
    rank = shape_region_address[0];
    log_info("rank %d\n", rank);

    // Reserve memory to DTCM
    shape_addr_dtcm = (uint32_t*) spin1_malloc(rank * sizeof(uint32_t));
    // Copy values to DTCM
    spin1_memcpy(shape_addr_dtcm, &shape_region_address[1], rank * sizeof(uint32_t));

    // read my const value
    address_t input_region_address = data_specification_get_region(INPUT, address);
    input_size = input_region_address[0];
    log_info("input_size %d\n", input_size);

    // Reserve memory for DTCM
    input_addr_dtcm = (uint32_t*) spin1_malloc(input_size * sizeof(uint32_t));
    // Copy values to DTCM
    spin1_memcpy(input_addr_dtcm, &input_region_address[1], input_size * sizeof(uint32_t));

    for(int i=0; i<input_size; i++){
        //Store values in DTCM
        log_info("array value %d\n", input_addr_dtcm[i]);
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

    // kick-start the process
    spin1_schedule_callback(update, 0, 0, USER);

    // start execution
    log_info("Starting\n");

spin1_start(SYNC_WAIT);

}
