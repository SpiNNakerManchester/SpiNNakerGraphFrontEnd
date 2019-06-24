
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>

int size = 0;
int value_a;
int value_b;
int counter = 0;
int result = 0;
uint32_t pre_vertex1_key;
uint32_t pre_vertex2_key;
uint my_key;
int is_matrix=0;
int rank =0;
// key | value
int** shape1;
int shape_counter=0;

int** tensor1;
int tensor_counter=0;

uint32_t oper_type = 0;

uint key_exist = 0; 

address_t address = NULL;

typedef enum regions_e {
    PREVERTEX_KEYS,
    OPER_TYPE,
    TRANSMISSIONS,
    RECORDED_DATA
} regions_e;


typedef enum callback_priorities{
    MC_PACKET = -1, USER = 3
} callback_priorities;


typedef enum oper_type_region_element {
    OPER_TYPE_POSITION
} initial_state_region_elements;


typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;


void send_value(uint data){
    log_info("addition send_value\n", my_key);

    log_info("sending value via multicast with key %d",
              my_key);
    while (!spin1_send_mc_packet(my_key, data, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

}

void record_data(int result) {
    log_info("Recording data\n");

    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    spin1_memcpy(record_space_address, &result, 4);
    log_info("recorded result %d address: %u\n", result ,record_space_address);

}

int addition(int a, int b){
    log_info("addition\n");
    int sum;
    log_info("Addition of A %d and B %d \n", a , b);
    sum = a + b;
    log_info("Addition Result : %d \n", sum);
    return sum;
}

// Todo : specify which value is Substracted after the reception.
int sub(int a, int b){
    log_info("subtraction\n");
    int res;
    log_info("Subtraction from A %d the value B %d \n", a , b);
    res = a - b;
    log_info("Subtraction Result : %d \n", res);
    return res;
}


int a[2][3] = {
    {1, 2, 3},
    {4, 5, 6}
};

int b[3][2] = {
    {7, 8},
    {9, 10},
    {11,12}
};

int multiply[][2];

// int* mat_mul(int a[][N], int* shape_a, int b[][N], int* shape_b){
void mat_mul(){

    log_info("mat_mul\n");

    for(int row=0; row<2; row++){
        for(int col=0; col<2; col++){
            for(int i=0; i<3; i++){
                multiply[row][col] += a[row][i] * b[i][col];
                log_info("Mul %d", multiply[row][col]);
            }
        }
    }
    // for(int row=0; i<shape_a[0]; i++)
    //     for(int col=0; j<shape_b[1]; j++)
    //         for(int i=0; i<shape_a[1] ;i++)
    //             multiply[row][col] = a[row][i] + b[i][col]
}

int mul(int a, int b){
    log_info("multiplication\n");
    int res;
    log_info("Mul of A %d and B %d \n", a , b);
    res = a * b;
    log_info("Mul Result : %d \n", res);
    return res;
}

// Todo : Handling of cast values of Tensorflow.
int div(int a, int b){
    log_info("division\n");
    int res;
    log_info("Division from A %d the value B %d \n", a , b);
    res = a / b;
    log_info("Division Result : %d \n", res);
    return res;
}

void receive_data(uint key, uint payload) {
    log_info("receive key %d and data %d\n", key, payload);

    counter +=1;

    // Check size of vertex 1
    if (key == pre_vertex1_key && payload > 1){
        log_info("V1:size is greater than 1, matrix reception");
        size = payload;
        is_matrix = 1;
    }
    // If matrix get rank
    else if (is_matrix ==1 && key == pre_vertex1_key+1){
        log_info("V1:rank received %d\n", payload);
        rank = payload;
        shape1 = (uint32_t*) spin1_malloc(rank * sizeof(uint32_t));
    }
    // Get Shape of Tensor
    else if (is_matrix ==1 && key > pre_vertex1_key+1 && key <= pre_vertex1_key+1+ rank){
        log_info("V1:Dimesion Received %d\n", payload);
        shape1[shape_counter] = (uint32_t*) spin1_malloc(2 * sizeof(uint32_t));
        shape1[shape_counter][0] = key;
        shape1[shape_counter][1] = payload;
        log_info("V1:shape_counter%d\n", shape_counter);
        log_info("V1:Shape packet, key     [%d][0]%d\n",shape_counter, shape1[shape_counter][0]);
        log_info("V1:Shape packet, payload [%d][1]%d\n",shape_counter, shape1[shape_counter][1]);

        ++shape_counter;
    }

    // Get Tensor values
    else if (key > pre_vertex1_key+1+ rank && key <= pre_vertex1_key+1+ rank + size){
        log_info("V1:Tensor value Received %d\n", payload);
        tensor1[tensor_counter] = (uint32_t*) spin1_malloc(2 * sizeof(uint32_t));
        tensor1[tensor_counter][0] = key;
        tensor1[tensor_counter][1] = payload;
        log_info("V1:tensor_counter%d\n", tensor_counter);
        log_info("V1:tensor1 packet, key     [%d][0]%d\n",tensor_counter, tensor1[tensor_counter][0]);
        log_info("V1:tensor1 packet, payload [%d][1]%d\n",tensor_counter, tensor1[tensor_counter][1]);

        ++tensor_counter;
    }

    // if(counter == 1){
    //     value_a = payload;
    // }
    // else{
    //     value_b = payload;

    //     if(oper_type == 1){
    //         result = addition(value_a, value_b);
    //     }

    //     if(oper_type == 2){
    //         result = mul(value_a, value_b);
    //     }

    //     if(oper_type == 3){
    //         result = sub(value_a, value_b);
    //     }

    //     // if(oper_type == 4){
    //     //     
    //     // }

    //     // if(oper_type == 5){
    //     //     result = div(value_a, value_b);
    //     // }

    //     if(key_exist == 1){
    //         send_value(result);
    //     }
  
    //     record_data(result);
    //     spin1_exit(0);

    // }
    
}

static bool initialize() {
    log_info("Initialise addition: started\n");

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
    pre_vertex2_key = prevertex_keys_region_address[1];
    log_info("prevertex 1 key is %d\n", pre_vertex1_key);
    log_info("prevertex 2 key is %d\n", pre_vertex2_key);

    // read my oper type value
    address_t oper_type_region_address = data_specification_get_region(OPER_TYPE, address);
    oper_type = oper_type_region_address[OPER_TYPE_POSITION];
    log_info("my oper type value is %d\n", oper_type);

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
        log_info("Addition vertex without key, just perform the addition and record the result");
    }

    // mat_mul();

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
    log_info("starting Tensor operation\n");

    // initialise the model
    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    log_info("Starting\n");

spin1_start(SYNC_WAIT);
}
