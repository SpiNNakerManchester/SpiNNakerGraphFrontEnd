/***** master.c/master_summary
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
#include "put.h"
#include "../sdp_utils.h"
#include <data_specification.h>
#include <sark.h>
#include <circular_buffer.h>
#include "../double_linked_list.h"
#include "../message_queue.h"
//#include "eieio_interface.h"
//#include "reverse_iptag_multicast_source.c"

#include <debug.h>

// Globals
uint32_t time               = 0;

static circular_buffer sdp_buffer;

const double_linked_list* unacknowledged_puts;
const double_linked_list* recent_messages_queue;

/*  Send acknowledgement to core which replied to a PULL request. */

/*
void master_pull_reply_ack(uint32_t message_id, uint32_t core_id){
    sdp_msg_t* msg = create_internal_sdp_header(core_id);

    msg->cmd_rc      = MASTER_PULL_REPLY_ACK;
    msg->seq         = message_id;

    msg->length      = sizeof(sdp_hdr_t) + 16;

    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
}
*/

void master_pull(sdp_msg_t* msg){

    //address_t address_k = append(master_k_current_addr, k,1); // Store into sdram and pass a pointer to it

    //msg->srce_addr   = spin1_get_chip_id();
    //msg->srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    // Message source is still BOSS

    // Destination core is on the same chip

    for(int i=FIRST_SLAVE; i<=LAST_SLAVE; i++){
        sdp_msg_t* msg_cpy = (sdp_msg_t*) sark_alloc(1,sizeof(sdp_msg_t));
        sark_msg_cpy(msg_cpy, msg);

        msg_cpy->dest_addr   = spin1_get_chip_id();
        msg_cpy->dest_port   = (SDP_PORT << PORT_SHIFT) | i;

        spin1_send_sdp_msg(msg_cpy, SDP_TIMEOUT); //message, timeout
    }
}
/*
void master_pull_retry(unreplied_query* q){
    if(!q){return;}

    q->retries++;

    master_pull_r(q->info, q->data, true, q->message_id);

    if(q->retries >= MAX_RETRIES){

        log_info("PULL at [time: %d, rtt: %d, retries: %d] -> NULL (tried too many times)",
                 time, time - q->time_sent, q->retries);

        remove_from_unreplied_queue(unreplied_pulls, q->message_id); //todo ineffient removing here like this
    }
}
*/

core_data_address_t* core_data_addresses;

void quick_clear(){
    for(int i=FIRST_SLAVE; i <= LAST_SLAVE; i++){
        //set data written for each core to zero. Similar to quick format. The data still exists
        **core_data_addresses[i].data_start = 0;
        *core_data_addresses[i].data_current = *core_data_addresses[i].data_start+1;
    }
}

uint8_t  core_with_less_data = FIRST_SLAVE;

bool balanced_put(uint32_t info, void* k, void* v){

    bool success = put(core_data_addresses[core_with_less_data], info, k, v);

    for(int i=FIRST_SLAVE; i <= LAST_SLAVE; i++){
        if(**core_data_addresses[i].data_start < **core_data_addresses[core_with_less_data].data_start){
            core_with_less_data = i;
        }
    }

    return success;

}

void update (uint ticks, uint b)
{
    time++;

    if(ticks == 50){ //todo..... do I need to give time for cores to get ready?
        //ignore 0,1 and 17
        for(int i=2; i<NUM_CPUS-1; i++){
            core_data_addresses[i] = get_core_data_address(i);
        }

        print_core_data_addresses(core_data_addresses);
    }

    return; //todo for now

    age_recently_received_queries(recent_messages_queue);
}

void sdp_packet_callback(uint mailbox, uint port) {

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }

}

void process_requests(uint arg0, uint arg1){

    uint32_t* mailbox_ptr;
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){


        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        /*
        if(is_duplicate_query(recent_messages_queue, msg->seq)){
            log_info("Duplicate. Ignore.");
            spin1_msg_free(msg);
            return; //duplicate
        }
        else{
            //print_msg(msg);
            push(recent_messages_queue, init_recently_received_query(msg->seq));
        }
        */

        //push(recent_messages_queue, init_recently_received_query(msg->seq));

        uint32_t info = msg->arg1;

        log_info("received something....");

        switch(msg->cmd_rc){
            case PUT:; //coming from boss
                                        log_info("Received put request");
                                        bool p = balanced_put(info, msg->data, &msg->data[k_size_from_info2(info)]);

                                        revert_src_dest(msg);
                                        msg->cmd_rc = PUT_REPLY;

                                        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                                        break;
            case PULL:; //coming from boss
                                        log_info("Received pull request");

                                        //push(unreplied_pulls, init_unreplied_query(msg));

                                        master_pull(msg);
                                        break;
            case CLEAR:;                log_info("Received clear request");
                                        quick_clear();
                                        break;
            case PULL_REPLY:;  //coming from SLAVE

                               /*
                                        log_info("Received pull reply");
                                        void* v = msg->data; //pointer to the data from master

                                        unreplied_query* uq = remove_from_unreplied_queue(unreplied_pulls, msg->seq);

                                        if(!uq){  //we are not expecting this PULL reply anymore (may be a duplicate)
                                            break;
                                        }

                                        //forward it to
                                        msg->dest_port = uq->srce_port;
                                        msg->dest_addr = uq->srce_addr;

                                        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                                        //master_pull_reply_ack(msg->seq, msg->srce_port & 0x1F);// todo can just be the port itself...
                               */
                                        break;
            default:            log_info("Received invalid request...");
                                break;
        }

        // free the message to stop overload
        spin1_msg_free(msg);
    }
}

void c_main()
{
    log_info("Initializing Master for chip %04x", spin1_get_chip_id());

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    //Global assignments
    //unreplied_pulls = init_double_linked_list();
    recent_messages_queue = init_double_linked_list();

    core_data_addresses = (core_data_address_t*) sark_alloc(NUM_CPUS, sizeof(core_data_address_t));

    // set timer tick value to 100 milliseconds
    spin1_set_timer_tick(100);

    sdp_buffer = circular_buffer_initialize(100); //todo size...

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, -1);
    spin1_callback_on(USER_EVENT,       process_requests,    1);
    spin1_callback_on(TIMER_TICK,       update,              2);

    simulation_run();
}