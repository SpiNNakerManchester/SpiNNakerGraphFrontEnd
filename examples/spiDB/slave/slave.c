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
#include <debug.h>
#include <simulation.h>

#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "../sdram_writer.h"
#include "../sdp_utils.h"
#include "pull.h"

#include "unit_tests/pull_tests.c"
#include "../double_linked_list.h"
#include "../message_queue.h"

//Globals
uint32_t time = 0;


double_linked_list* unacknowledged_replies;
double_linked_list* recent_messages_queue;

/*
void sdp_reply_pull_request_r(uint32_t info, void* v, uint32_t message_id, bool is_retry){

    sdp_msg_t* reply = create_internal_sdp_header(MASTER_CORE_ID);

    reply->cmd_rc = SLAVE_PULL_REPLY; //reply from a pull request //todo is this how i should do it?
    reply->seq    = message_id;
    reply->arg1   = info;
    reply->arg2   = v;
    reply->arg3   = NULL;

    reply->length      = sizeof(sdp_hdr_t) + 16; //+ k_size + v_size

    spin1_send_sdp_msg(reply, SDP_TIMEOUT); //message, timeout

    //we expect an acknowledgement on the reply

    if(!is_retry){ //Ie first time it's sent
        push(unacknowledged_replies, init_unreplied_query_from_msg(*reply));
    }
}

void sdp_reply_pull_request(uint32_t info, void* v, uint32_t message_id){
    sdp_reply_pull_request_r(info, v, message_id, false);
}

void sdp_reply_pull_request_retry(uint32_t info, void* v, uint32_t message_id){
    sdp_reply_pull_request_r(info, v, message_id, true);
}
*/

void update(uint ticks, uint b){
    time++;

    /*
    age_recently_received_queries(recent_messages_queue);

    if(time % 10 == 0 && unacknowledged_replies->size > 0){

        list_entry* entry = *unacknowledged_replies->head;

        while(entry != NULL){

            unreplied_query* q = (unreplied_query*)entry->data;
            q->retries++;

            log_info("Retrying id %d ", q->message_id);
            sdp_reply_pull_request_retry(q->info, q->data, q->message_id);

            if(q->retries >= MAX_RETRIES){
                log_info("Tried sending message id %d too many times. Removing from queue", q->message_id);
                remove_from_unreplied_queue(unacknowledged_replies,q->message_id); //todo ineffient removing here like this
            }

            entry = entry->next;
        }
    }
    */

}

void sdp_packet_callback(uint mailbox, uint port) {

    sdp_msg_t* msg = (sdp_msg_t*) mailbox;

    uint32_t info = msg->arg1;
    void* k       = msg->data; //pointer to the data from master

    switch(msg->cmd_rc){
        case PULL:; log_info("Received PULL id %d", msg->seq);
                            //log_info("Received PULL id %d on k=%d", msg->seq, *((uint32_t*)k));

                    if(is_duplicate_query(recent_messages_queue, msg->seq)){
                        log_info("Duplicate. Ignore.");
                        break; //duplicate
                    }
                    else{
                        //log_info("Received a unique PULL request at TIME * %d * with id %d on k %d (%s)",
                        //         time, msg->seq, *((uint32_t*)k), (char*)k);
                        push(recent_messages_queue, init_recently_received_query(msg->seq));
                    }

                    value_entry* value_entry_ptr = pull(info, k);

                    if(value_entry_ptr){
                        log_info("Replying PULL request id %d at time * %d * with data (s: %s)",
                                 msg->seq, time, (char*)value_entry_ptr->data);

                        revert_src_dest(msg);
                        msg->cmd_rc = PULL_REPLY;
                        msg->arg1 = to_info1(value_entry_ptr->type, value_entry_ptr->size); //or simply use arg2 arg3
                        memcpy(msg->data, value_entry_ptr->data, value_entry_ptr->size);

                        print_msg(msg);

                        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                    }
                    else{ //do not reply
                        log_info("Not found...");
                    }
                    break;
        /*
        case MASTER_PULL_REPLY_ACK:     log_info("Received pull acknowledgement at %d. Removing id %d from queue.", time, msg->seq);
                                        if(!remove_from_unreplied_queue(unacknowledged_replies, msg->seq)){
                                            log_info("[Warning] Pull reply ACK did not belong to me!!"); //or was too old... don't know
                                        }
                                        break;

        case SLAVE_PULL_REPLY:;         log_info("[WARNING] Slave received PULL_REPLY query.");
                                        break;
        */
        default:                log_info("[Warning] cmd_rc not recognized: %d WITH ID %d from core %d", msg->cmd_rc, msg->seq, msg->srce_port & 0x1F);
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

    recent_messages_queue   = init_double_linked_list();
    unacknowledged_replies  = init_double_linked_list();


    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 1);
    spin1_callback_on (SDP_PACKET_RX, sdp_packet_callback, 0); //change priorities

    simulation_run();
}