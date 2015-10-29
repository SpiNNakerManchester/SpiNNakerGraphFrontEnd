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
#include "../sdram_writer.h"
#include "../sdp_utils.h"
#include "pull.h"

#include <debug.h>
#include <simulation.h>
#include "unit_tests/pull_tests.c"

#define MASTER_CORE_ID 1

/*
void send_db_region_address(){
    sdp_msg_t msg = create_sdp_header(DB_MASTER_CORE);

    msg.cmd_rc = SEND_DATA_REGION;
    msg.seq    = 1;
    msg.arg1   = writer.start; //how about the end?

    msg.length      = sizeof(sdp_hdr_t) + 16;
    print_msg(msg);

    spin1_send_sdp_msg(&msg, SDP_TIMEOUT); //message, timeout
}
*/

void update(uint ticks, uint b)
{
    if(ticks == 5){
        //send_db_region_address();
        //run_pull_tests();
        //run_put_tests();
    }
}


void sdp_reply_pull_request(value_entry* value_entry_ptr){

    sdp_msg_t reply = create_sdp_header(MASTER_CORE_ID);

    reply.cmd_rc = PULL; //reply from a pull request //todo is this how i should do it?
    reply.seq    = 1;
    reply.arg1   = to_info(value_entry_ptr->type, value_entry_ptr->size);
    reply.arg2   = value_entry_ptr->data;

    reply.length      = sizeof(sdp_hdr_t) + 16; //+ k_size + v_size

    spin1_send_sdp_msg(&reply, SDP_TIMEOUT); //message, timeout
}

void sdp_packet_callback(uint mailbox, uint port) {

    use(port); // TODO is this wait for port to be free?
    sdp_msg_t* msg = (sdp_msg_t*) mailbox;

    uint32_t info = msg->arg1;
    void* k = msg->arg2; //pointer to the data from master

    switch(msg->cmd_rc){
        case PULL:; log_info("Received a PULL request on k %d (%s)",*((uint32_t*)k), (char*)k);

                    value_entry* value_entry_ptr = pull(info, k);

                    if(value_entry_ptr){
                        log_info("*******   Replying with %d (%s)   ********",
                                 *((uint32_t*)value_entry_ptr->data), (char*)value_entry_ptr->data);
                        sdp_reply_pull_request(value_entry_ptr);
                    }
                    //else{
                        //log_info("Not replying because data was not found.");
                    //}
                    //if we don't find it, we don't reply
                    //todo should we reply with a 'didnt find'? but then overloads master core...

                    break;
        default:    log_info("cmd_rc not recognized: %d", msg->cmd_rc);
                    break;
    }

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
    spin1_callback_on (SDP_PACKET_RX,        sdp_packet_callback, 1); //change priorities
    //spin1_callback_on(MC_PACKET_RECEIVED,   sdp_packet_callback, 1);
    //spin1_callback_on(MCPL_PACKET_RECEIVED, sdp_packet_callback, 1);

    simulation_run();
}