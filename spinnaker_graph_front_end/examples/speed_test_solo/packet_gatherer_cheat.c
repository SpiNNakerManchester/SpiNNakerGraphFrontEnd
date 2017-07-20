
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

#define ITEMS_PER_DATA_PACKET 64

static uint32_t data[ITEMS_PER_DATA_PACKET];
static uint32_t position_in_store = 0;
static uint32_t use_seq;
sdp_msg_t my_msg;

static uint32_t bytes_to_write;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION, CONFIG
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, SDP = 0, DMA = 0
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum config_region_elements {
    MB, ADD_SEQ
} config_region_elements;

void send_data(){
   //log_info("last element is %d", data[position_in_store - 1]);
   //log_info("first element is %d", data[0]);
   spin1_memcpy(&my_msg.cmd_rc, (void *)data, position_in_store * 4);
   my_msg.length = 8 + (position_in_store * 4);
   while(!spin1_send_sdp_msg (&my_msg, 1000)){

   }
   position_in_store = 0;
}


void start_data(){
    uint iterations = (uint)(bytes_to_write / 4);
    log_info("iteration is %d", iterations);
    data[0] = bytes_to_write;
    position_in_store = 1;
    uint32_t seq_num = 0;
    for(uint count = 0; count < iterations; count++){
        if(position_in_store == 0 && use_seq == 1){
            data[position_in_store] = seq_num;
            position_in_store +=1;
            seq_num +=1;
        }
        data[position_in_store] = count;
        position_in_store += 1;
        if (position_in_store == ITEMS_PER_DATA_PACKET){
            send_data();
        }
    }
    log_info("sending final state");
    data[position_in_store] = 0xFFFFFFFF;
    position_in_store +=1;
    send_data();
}

void sdp(uint mailbox, uint port){
    log_info("packet received");
    sdp_msg_t *msg = (sdp_msg_t *) mailbox;
    spin1_msg_free(msg);
    start_data();

}


void resume_callback() {
    time = UINT32_MAX;
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

    address_t config_address = data_specification_get_region(
        CONFIG, address);
    bytes_to_write = config_address[MB];
    use_seq = config_address[ADD_SEQ];

    log_info("bytes to write is %d", bytes_to_write);

    my_msg.tag = 1;                    // IPTag 1
    my_msg.dest_port = PORT_ETH;       // Ethernet
    my_msg.dest_addr = sv->eth_addr;   // Nearest Ethernet chip

    // fill in SDP source & flag fields
    my_msg.flags = 0x07;
    my_msg.srce_port = 3;
    my_msg.srce_addr = sv->p2p_addr;

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

    uint32_t timer_period;
    log_info("starting packet gatherer\n");

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    simulation_sdp_callback_on(2, sdp);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
