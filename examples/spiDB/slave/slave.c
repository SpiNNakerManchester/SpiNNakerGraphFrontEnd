/***** slave.c/slave_summary
*
* COPYRIGHT
*  Copyright (c) The University of Manchester, 2011. All rights reserved.
*  SpiNNaker Project
*  Advanced Processor Technologies Group
*  School of Computer Science
*  Author: Arthur Ceccotti
*******/

#include "spin1_api.h"
#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "put.h"
#include "pull.h"

#include <debug.h>
#include <simulation.h>
#include "unit_tests/put_tests.c"
#include "unit_tests/pull_tests.c"

static bool initialize() {

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpec data address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read Dataspec header");
        return false;
    }

    address_t system_region = data_specification_get_region(SYSTEM_REGION, address);
    address_t data_region   = data_specification_get_region(DB_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    uint32_t data_region_size = 500;

    recording_init(data_region, data_region_size);

    //todo clear data at the start?

    log_info("Initialization completed successfully!");
    return true;
}

void update(uint ticks, uint b)
{
    if(ticks == 100){
        //run_pull_tests();
        //run_pull_tests();
    }
}

void sdp_packet_callback(uint mailbox, uint port) {
    log_info("Received a packet...");

    use(port); // TODO is this wait for port to be free?
    sdp_msg_t* msg = (sdp_msg_t*) mailbox;

    print_msg(*msg);

/*    uint32_t info = msg->arg1;
    uint v_type_and_size = msg->arg2;*/


    //uchar k = msg->data[0]; //TODO !!!!!!!! REALLY SHOULD DO WORD->ARR OF BYTES
    //uchar v = msg->data[4]; //TODO same here...

/*    switch(msg->cmd_rc){
        case PUT: put(k_type_and_size,v_type_and_size, &k, &v);
                  break;
        default:
                 break;
    }*/

    // free the message to stop overload
    spin1_msg_free(msg);
}

void c_main()
{
    log_info("Initializing Slave...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }
    // set timer tick value to 100ms
    spin1_set_timer_tick(100); //todo should not be hardcoded


    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 0);
    spin1_callback_on(SDP_PACKET_RX,        sdp_packet_callback, 1);
    //spin1_callback_on(MC_PACKET_RECEIVED,   sdp_packet_callback, 1);
    //spin1_callback_on(MCPL_PACKET_RECEIVED, sdp_packet_callback, 1);

    simulation_run();
}