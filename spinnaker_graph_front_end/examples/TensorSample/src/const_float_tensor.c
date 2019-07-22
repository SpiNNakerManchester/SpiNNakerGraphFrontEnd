
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>


uint my_key;

int const_value;
int rank=0;
int input_size;
uint32_t *shape_addr_dtcm;
float *input_addr_dtcm;

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


static inline uint float_to_int(float f) {
    union {
        float f;
        uint u;
    } value;
    value.f = f;
    return value.u;
}

// unit8 to float converter

void send_value(){
    log_info("send_value method \n");
    log_info("first key %d\n", my_key);

    // send size
    log_info("send key %d and input_size %d\n", my_key, input_size);
    while (!spin1_send_mc_packet(my_key, input_size, WITH_PAYLOAD)) {
       spin1_delay_us(1);
    }

    // send rank and shape
    my_key += 1;

    if(input_size > 1){
        log_info("send key %d and rank %d\n", my_key, rank);
        while (!spin1_send_mc_packet(my_key, rank, WITH_PAYLOAD)) {
            spin1_delay_us(1);
        }
    

        for(int i=0; i<rank; i++){
            my_key += 1;
            log_info("send key %d and dim value %d\n", my_key, shape_addr_dtcm[i]);
            while (!spin1_send_mc_packet(my_key, shape_addr_dtcm[i], WITH_PAYLOAD)) {
                spin1_delay_us(1);
            }
        }
    }

    // send tensor values
    for(int i=0; i<input_size; i++){
        my_key += 1;
        // log_info("send key %d and tensor value %x \n", my_key,float_to_int(input_addr_dtcm[i]));
        while (!spin1_send_mc_packet(my_key, float_to_int(input_addr_dtcm[i]), WITH_PAYLOAD)) {
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
    log_info("Initialise const_float_tensor: started\n");

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
// todo i have to create a struct that describes a memory

    // read my const value
    address_t input_region_address = data_specification_get_region(INPUT, address);
    input_size = input_region_address[0];
    log_info("input_size %d\n", input_size);

    // Reserve memory for DTCM
    // input_addr_dtcm = (float*) spin1_malloc(input_size * sizeof(float));
    // if(input_addr_dtcm == NULL){
    //     log_error("DTCM is full");
    //     rt_error(RTE_SWERR);
    // }

// use instead sdram to put it
    input_addr_dtcm = (float*) sark_xalloc(sv->sdram_heap, input_size * sizeof(float), 0, ALLOC_LOCK);


    // Copy values to DTCM
    spin1_memcpy(input_addr_dtcm, &input_region_address[1], input_size * sizeof(float));


    if (input_size >1){
        // read my shape
        address_t shape_region_address = data_specification_get_region(TENSOR_PROPERTIES, address);
        rank = shape_region_address[0];
        log_info("rank %d\n", rank);

        // Reserve memory to DTCM
        shape_addr_dtcm = (uint32_t*) spin1_malloc(rank * sizeof(uint32_t));
        // Copy values to DTCM
        spin1_memcpy(shape_addr_dtcm, &shape_region_address[1], rank * sizeof(uint32_t));
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