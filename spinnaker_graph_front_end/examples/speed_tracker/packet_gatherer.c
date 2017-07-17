
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
sdp_msg_t my_msg;


//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, SDP = 0, DMA = 0
} callback_priorities;


void resume_callback() {
    time = UINT32_MAX;
}

void send_data(){
   spin1_memcpy(my_msg.data, (void *)data, position_in_store * 4);
   my_msg.length = position_in_store * 4;
   (void) spin1_send_sdp_msg (&my_msg, 100);
   position_in_store = 0;
}

void receive_data(uint key, uint payload){

    data[position_in_store] = payload;
    position_in_store += 1;

    if(position_in_store == ITEMS_PER_DATA_PACKET){
        send_data();
    }

   // check key seq num for missing things if required.
   use(key);
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
    log_info("starting heat_demo\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
