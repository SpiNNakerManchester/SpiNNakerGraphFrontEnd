//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>


int value_a;
int value_b;
int counter = 0;
int expected_packets=0;

// Transmission info
uint my_key;
uint32_t pre_vertex1_key;
uint32_t pre_vertex2_key;
int is_matrix1=0;
int is_matrix2=0;

// Tensor properties
int size1 = 0;
int size2 = 0;
int rank1 =0;
int rank2 =0;
uint32_t* shape1;
uint32_t* shape2;
uint32_t* tensor1;
uint32_t* tensor2;

uint32_t* multiply;

uint key_exist = 0;
address_t address = NULL;

typedef enum regions_e {
    PREVERTEX_KEYS,
    TENSOR1_PROPERTIES,
    TENSOR2_PROPERTIES,
    TRANSMISSIONS,
    RECORDED_DATA
} regions_e;

typedef enum callback_priorities{
    MC_PACKET = -1, USER = 3
} callback_priorities;

typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;

void send_value(uint data){
    log_info("mat_mul send_value\n", my_key);
    // send tensor values
    for(int i=0; i<size1; i++){
        log_info("send key %d and tensor value %d\n", my_key, tensor1[i]);
        while (!spin1_send_mc_packet(my_key, tensor1[i], WITH_PAYLOAD)) {
            spin1_delay_us(1);
        }
        my_key += 1;
    }
}

void record_data() {
    log_info("Recording data\n");

    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    spin1_memcpy(record_space_address, multiply, 4);
    log_info("recorded result %d address: %u\n", multiply[0] ,record_space_address);

}

void softmax(){
    log_info("softmax\n");

    // float normal_exp[6];
    // float tensor2[7] = {1, 2, 3, 4, 1, 2, 3};     // shape = [1 ,7]
    // int shape2[2] = {1, 7};
    // float sum_exp_row[shape2[0]];

    for (int i=0; i<shape1[0]; i++){
    for (int k=0; k<shape1[1]; k++){
        printf("%f \n",tensor1[k+i*shape1[1]]);
        printf("%f \n",exp(tensor1[k+i*shape1[1]]));

        sum_exp_row[i]+= exp(tensor1[k+i*shape1[1]]);
    }
    log_info("sum of row is %f \n",sum_exp_row[i]);
}

    for (int i=0; i<shape1[0]; i++){
        for (int j=0; j<shape1[1]; j++){
            normal_exp[i] = exp(tensor1[j+i*shape1[1]])/ sum_exp_row[i];
            log_info("normal_exp %d : %f \n",i, normal_exp[i]);
        }
    }

}

void receive_data(uint key, uint payload) {
    // log_info("key %d , data %d\n", key, payload);
    ++counter;
    // Check size1 of vertex 1
    if (key >= pre_vertex1_key && key < pre_vertex1_key + size1 ){
        tensor1[key] = payload;
        log_info("V1:key %d ,V1:tensor1 value %d\n", key, tensor1[key]);
    }

    if(counter == size1 ) {
        log_info("tensor received\n");
        softmax();
        record_data();
        spin1_exit(0);
    }
    
}

static bool initialize() {
    log_info("Initialise softmax_nd: started\n");

    // Get the address this core's DTCM data starts at from SDRAM
    address = data_specification_get_data_address();
    log_info("address is %u\n", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // read prevertex keys
    address_t prevertex_keys_region_address = data_specification_get_region(PREVERTEX_KEYS, address);
    pre_vertex1_key = prevertex_keys_region_address[0];
    log_info("prevertex 1 key is %d\n", pre_vertex1_key);

    // read tensor1 properties
    address_t t_prop1_region_address = data_specification_get_region(TENSOR1_PROPERTIES, address);
    size1 = t_prop1_region_address[0];
    log_info("size1 %d\n", size1);
    rank1 = t_prop1_region_address[1];
    log_info("rank1 %d\n", rank1);
    // Reserve memory to DTCM
    shape1 = (uint32_t*) spin1_malloc(rank1 * sizeof(uint32_t));
    // Copy values to DTCM
    spin1_memcpy(shape1, &t_prop1_region_address[2], rank1 * sizeof(uint32_t));
    log_info(" shape1 %d :\n", shape1[0]);
    log_info(" shape1 %d :\n", shape1[1]);

    tensor1 = (uint32_t*) spin1_malloc(size1 * sizeof(uint32_t));

    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    log_info("transmission_region_address  is %u\n", transmission_region_address);
    // a pointer to uint32 and if the first element of this array exists so has key do the code bellow
    if (transmission_region_address[HAS_KEY] == 1) {
        key_exist = 1;
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    } else {
        log_info("softmax_nd vertex without key, no sending packets");
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
    log_info("starting softmax_nd \n");

    // initialise the model
    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    log_info("Starting\n");

spin1_start(SYNC_WAIT);
}
