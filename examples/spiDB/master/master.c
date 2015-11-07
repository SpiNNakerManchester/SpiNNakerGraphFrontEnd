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
#include "../double_linked_list.h"
#include "../message_queue.h"
//#include "eieio_interface.h"
//#include "reverse_iptag_multicast_source.c"

#include <debug.h>

// Globals
uint32_t time               = 0;
uint32_t current_message_id = 0;

const double_linked_list* unreplied_pulls;

address_t* master_k_current_addr;

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
    msg->dest_addr   = spin1_get_chip_id();

    for(int i=FIRST_SLAVE; i<=LAST_SLAVE; i++){
        //sdp_msg_t* msg = create_internal_sdp_header(i);


        msg->dest_port   = (SDP_PORT << PORT_SHIFT) | i;

        // ======================== SCP ========================
        /*
        msg->cmd_rc      = PULL;
        msg->seq         = message_id;

        msg->arg1        = info;
        msg->arg2        = address_k;
        msg->arg3        = NULL;

        msg->length      = sizeof(sdp_hdr_t) + 16;
        */

        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
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

uint32_t p = 2;

bool round_robin_put(uint32_t info, void* k, void* v){

    log_info("Put data at %08x", core_data_addresses[p].data_start);

    bool success = put(core_data_addresses[p++], info, k, v);

    if(p > LAST_SLAVE){ p = FIRST_SLAVE; }

    return success;
}

void update (uint ticks, uint b)
{
    time++;

    if(ticks == 50){
        //ignore 0,1 and 17
        for(int i=2; i<NUM_CPUS-1; i++){
            core_data_addresses[i] = get_core_data_address(i);
        }

        print_core_data_addresses(core_data_addresses);
    }


    /*
    if(ticks > 50 && ticks % 10 == 0 && unreplied_pulls->size > 0){

        list_entry* entry = *unreplied_pulls->head;

        while(entry != NULL){

            unreplied_query* q = (unreplied_query*)entry->data;

            master_pull_retry(q);

            entry = entry->next;
        }
    }
    */
}

/*
    if(!is_retry){ //Ie first time it's sent
        push(unreplied_pulls, init_unreplied_query(MASTER_PULL, current_message_id, info, k));
        current_message_id++;
    }
*/

void sdp_packet_callback(uint mailbox, uint port) {

    sdp_msg_t* msg = (sdp_msg_t*) mailbox;
    log_info("Received a packet!!!!!!!!!!!!!!!!!!!!");
    //print_msg(msg);

    uint32_t info = msg->arg1;

    switch(msg->cmd_rc){
        case PUT:; //coming from boss
                                    log_info("Doing round robin put");

                                    bool p = round_robin_put(info, msg->data, &msg->data[k_size_from_info2(info)]);

                                    //what if it failed? todo

                                    revert_src_dest(msg);
                                    msg->cmd_rc = PUT_REPLY;
                                    //todo trim data

                                    log_info("replying back...");
                                    print_msg(msg);
                                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                                    break;
        case PULL:; //coming from boss
                                    log_info("Received pull request");

                                    //push(unreplied_pulls, init_unreplied_query(msg));

                                    master_pull(msg);
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
        default:
                    break;
    }

    // free the message to stop overload
    spin1_msg_free(msg);
}

void c_main()
{
    log_info("Initializing Master for chip %04x", spin1_get_chip_id());

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    //Global assignments
    unreplied_pulls = init_double_linked_list();

    core_data_addresses = (core_data_address_t*) sark_alloc(NUM_CPUS, sizeof(core_data_address_t));

    master_k_current_addr  = (address_t*) sark_alloc(1, sizeof(address_t));
    *master_k_current_addr = data_region;

    // set timer tick value to 100ms
    spin1_set_timer_tick(100);

    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 1);
    spin1_callback_on (SDP_PACKET_RX, sdp_packet_callback, -1);

    simulation_run();
}