
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

//! The recording flags
static uint32_t recording_flags = 0;

static uint32_t *data[2];
static uint32_t dma_pointer = 0;
static uint32_t position = 0;

static uint32_t key;
static uint32_t bytes_to_write;

#define ITEMS_PER_DATA_PACKET 64

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    RECORDED_DATA,
    CONFIG,
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
   SDP = 0, DMA = 0
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    MY_KEY, MB
} transmission_region_elements;

void resume_callback() {
    time = UINT32_MAX;
}

void sdp(uint mailbox, uint port){
    sdp_msg_t *msg = (sdp_msg_t *) mailbox;
    spin1_msg_free(msg);
    read();
}


void read(){

    // send length as first element.
    spin1_send_mc_packet(key, bytes_to_write, WITH_PAYLOAD);

    // set off dma
    address_t address = data_specification_get_data_address();
    address_t recorded_data =
        data_specification_get_region(RECORDED_DATA, address);

    address_t data_sdram_position = &recorded_data[position];
    position += ITEMS_PER_DATA_PACKET;
    while (!spin1_dma_transfer(0, data_sdram_position, data[dma_pointer],
                               DMA_READ, ITEMS_PER_DATA_PACKET * 4)){
        log_info("stuck in here!");
    }
    dma_pointer = (dma_pointer + 1) % 2;
}


void send_data(uint unused, uint tag){
   use(unused);
   use(tag);

   // do dma
   uint32_t current_dma_pointer = dma_pointer;

   // stopping procedure
   if (position < (uint)bytes_to_write / 4){
      read();
   }

   // send data
   for (uint data_position = 0; data_position < ITEMS_PER_DATA_PACKET;
            data_position ++)
   {
        uint32_t current_data = data[current_dma_pointer][data_position];
        spin1_send_mc_packet(key, current_data, WITH_PAYLOAD);
   }

   // if end, send end flag
   if (position >= (uint)bytes_to_write / 4){
       spin1_send_mc_packet(key, 0xFFFFFFFF, WITH_PAYLOAD);
   }

}

void write_data(){
    // write data into sdram for reading later
    address_t address = data_specification_get_data_address();
    address_t recorded_data =
        data_specification_get_region(RECORDED_DATA, address);
    uint iterations = (uint)(bytes_to_write / 4);
    for( uint count = 0; count < iterations; count++){
        recorded_data[count] = count;
    }
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

    address_t config_address = data_specification_get_region(CONFIG, address);
    key = config_address[MY_KEY];
    bytes_to_write = config_address[MB];
    log_info("bytes to write is %d", bytes_to_write);

    for (uint32_t i = 0; i < 2; i++) {
        data[i] = (uint32_t*) spin1_malloc(
                ITEMS_PER_DATA_PACKET * sizeof(uint32_t));
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
    log_info("starting heat_demo\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // write data
    write_data();

    simulation_dma_transfer_done_callback_on(0, send_data);
    simulation_sdp_callback_on(2, sdp);


    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
