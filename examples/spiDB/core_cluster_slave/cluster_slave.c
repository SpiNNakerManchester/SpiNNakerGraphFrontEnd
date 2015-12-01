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
#include "put.h"

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

    return;

    age_recently_received_queries(recent_messages_queue);  //todo
}

void sdp_packet_callback(uint mailbox, uint port) {
    //log_info("======================================= Received request... mailbox: %08x", mailbox);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }

}


address_t* addr = NULL;

void process_requests(uint arg0, uint arg1){

    uint32_t* mailbox_ptr;
    //circular_buffer_print_buffer(sdp_buffer);
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){

        //log_info("======================================= Processing request... -> %08x", *mailbox_ptr);

        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        uint32_t info = msg->arg1;
        uchar* k_v    = msg->data;

        #ifdef DB_HASH_TABLE
            uint32_t hash = msg->arg2;
            uint32_t words_offset = ((hash & 0x0007FFFF) % CORE_DATABASE_SIZE_WORDS);

            *addr = (address_t)&data_region[words_offset];
        #endif

        value_entry* value_entry_ptr;

        switch(msg->cmd_rc){
            case PUT:;
                        log_info("PUT on address: %04x", *addr);

                        put(addr, info, k_v, &k_v[k_size_from_info(info)]);

                        revert_src_dest(msg);
                        msg->cmd_rc = PUT_REPLY;

                        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                        break;
            case PULL:;
                        log_info("PULL on address: %04x", *addr);

                        value_entry_ptr = pull(*addr,info, k_v);

                        if(value_entry_ptr){
                            log_info("Replying PULL request id %d at time * %d * with data (s: %s) of type %d, size %d",
                                     msg->seq, time, value_entry_ptr->data, value_entry_ptr->type, value_entry_ptr->size);

                            revert_src_dest(msg);
                            msg->cmd_rc = PULL_REPLY;
                            //to_info1(value_entry_ptr->type, value_entry_ptr->size); //or simply use arg2 arg3

                            msg->arg1 = to_info(0, 0, value_entry_ptr->type, value_entry_ptr->size);

                            memcpy(msg->data, value_entry_ptr->data, value_entry_ptr->size);
                            msg->length = sizeof(sdp_hdr_t) + 16 + value_entry_ptr->size;

                            print_msg(msg);

                            spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                        }
                        else{ //TODO reply with not found!!!!!!!
                            log_info("Not found...");
                        }
                        break;
            /*
            case PUT_NAIVE:;
                         log_info("Received PULL NAIVE id %d on k=(%s) - Info %08x", msg->seq, k_v, info);

                         put(naive_current_addr, info, k_v, &k_v[k_size_from_info2(info)]);

                         revert_src_dest(msg);
                         msg->cmd_rc = PUT_NAIVE_REPLY;

                         spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                         break;

            case PULL_NAIVE:;
                        log_info("PULL NAIVE (h: %04x) on address: %04x", hash, addr);

                        //same as just data_address
                        value_entry_ptr = pull((address_t)&data_region[0],info, k_v);

                        if(value_entry_ptr){
                            log_info("Replying PULL request id %d at time * %d * with data (s: %s) of size %d",
                                     msg->seq, time, value_entry_ptr->data, value_entry_ptr->size);

                            revert_src_dest(msg);
                            msg->cmd_rc = PULL_NAIVE_REPLY;
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
            */

            /*
            case PULL:; log_info("Received PULL id %d on k=(%s) - Info %08x", msg->seq, k_v, info);

                        if(is_duplicate_query(recent_messages_queue, msg->seq)){
                            log_info("Duplicate. Ignore.");
                            break; //duplicate
                        }
                        else{
                            //log_info("Received a unique PULL request at TIME * %d * with id %d on k %d (%s)",
                            //         time, msg->seq, *((uint32_t*)k), (char*)k);
                            push(recent_messages_queue, init_recently_received_query(msg->seq));
                        }

                        value_entry* value_entry_ptr = pull(info, k_v);

                        if(value_entry_ptr){
                            log_info("Replying PULL request id %d at time * %d * with data (s: %s) of size %d",
                                     msg->seq, time, value_entry_ptr->data, value_entry_ptr->size);

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
            */
            default:    log_info("[Warning] cmd_rc not recognized: %d WITH ID %d from core %d", msg->cmd_rc, msg->seq, msg->srce_port & 0x1F);
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

    clear(data_region, CORE_DATABASE_SIZE_WORDS);

    addr = (address_t*)malloc(sizeof(address_t));
    *addr = (address_t)&data_region[0];

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