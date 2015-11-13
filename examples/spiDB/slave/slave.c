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
#include <circular_buffer.h>

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

static circular_buffer sdp_buffer;

void update(uint ticks, uint b){
    time++;

    return; //todo

    age_recently_received_queries(recent_messages_queue);

    /*
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
    log_info("======================================= Received request... mailbox: %08x", mailbox);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }

}

void process_requests(uint arg0, uint arg1){

    uint32_t* mailbox_ptr;
    circular_buffer_print_buffer(sdp_buffer);
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){

        log_info("======================================= Processing request... -> %08x", *mailbox_ptr);

        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        uint32_t info = msg->arg1;
        void* k       = msg->data; //pointer to the data from master

        log_info("msg->data[0] is %d:", msg->data[0]);
        log_info("msg->data[1] is %d:", msg->data[1]);
        log_info("msg->data[2is %d:", msg->data[2]);
        log_info("msg->data[3 is %d:", msg->data[3]);
        log_info("msg->data[4 is %d:", msg->data[4]);
        log_info("msg->data[5] is %d:", msg->data[5]);

        log_info("k is %08x", k);
        log_info("*((uint32_t*)k) %d", *((uint32_t*)k));

        switch(msg->cmd_rc){
            case PULL:; log_info("Received PULL id %d on k=(%s) - Info %08x", msg->seq, msg->data, info);
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
                            log_info("Replying PULL request id %d at time * %d * with data (s: %s) of size %d",
                                     msg->seq, time, (char*)value_entry_ptr->data, value_entry_ptr->size);

                            revert_src_dest(msg);
                            msg->cmd_rc = PULL_REPLY;
                            //to_info1(value_entry_ptr->type, value_entry_ptr->size); //or simply use arg2 arg3
                            msg->arg1 = value_entry_ptr->type;
                            msg->arg2 = value_entry_ptr->size;

                            memcpy(msg->data, value_entry_ptr->data, value_entry_ptr->size);
                            msg->length = sizeof(sdp_hdr_t) + 16 + value_entry_ptr->size;

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

    sdp_buffer = circular_buffer_initialize(100); //todo size...

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, -1);
    spin1_callback_on(USER_EVENT,       process_requests,    1);
    spin1_callback_on(TIMER_TICK,       update,              2);

    simulation_run();
}