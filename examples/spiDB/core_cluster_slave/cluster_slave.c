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
#include <data_specification.h>

#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "../memory_utils.h"
#include "../sdp_utils.h"
#include "pull.h"
#include "put.h"

#include "scan.h"

#include "../double_linked_list.h"
#include "../message_queue.h"

#define TIMER_PERIOD 100

//Globals
uint32_t time = 0;

double_linked_list* unacknowledged_replies;
//double_linked_list* recent_messages_queue;

static circular_buffer sdp_buffer;

uchar chipx;
uchar chipy;
uchar core;

Table* table;

void update(uint ticks, uint b){
    use(ticks);
    use(b);

    time += TIMER_PERIOD;

    //age_recently_received_queries(recent_messages_queue);
}

void sdp_packet_callback(uint mailbox, uint port) {
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }
}

address_t* addr;

uint32_t entriesInQueue = 0;
uchar entryQueue[60];//TODO 2-D array. Todo HARDCODED

void process_requests(uint arg0, uint arg1){

    uint32_t* mailbox_ptr;
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){

        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

        switch(header->cmd){
            case INSERT_INTO:;
                log_info("INSERT_INTO");
                insertEntryQuery* insertE = (insertEntryQuery*) header;
                Entry e = insertE->e;

                printEntry(&e);

                uint32_t i = get_col_index(e.col_name);
                uint32_t p = get_byte_pos(i); //todo very inefficient

                //todo double check that it is in fact empty (NULL)
                memcpy(&entryQueue[p], e.value, e.size);
                entriesInQueue++;

                if(entriesInQueue == table->n_cols){
                    uint32_t n = table->current_n_rows;

                    address_t address_to_write = data_region + ((table->row_size * n) + 3) / 4;

                    log_info("Flushed to %08x", address_to_write);

                    table->current_n_rows++; //todo concurrency!!!!!
                    entriesInQueue = 0; //reset and null all of them

                    write(address_to_write, entryQueue, table->row_size);

                    for(uint32_t i = 0; i < table->row_size; i++){
                        entryQueue[i] = 0;
                    }
                }

                //log_info("all %08x", data_region + (table->row_size * (e.row_id-1) + get_byte_pos(e.col_index) + 3) / 4);

                                                                //-1 because the row_id starts from 1
                //write(address_to_write,
                //      insertE->e.value,
                //      insertE->e.size); //assumes row_ids are 1,2,3,4,... single core TODO

                //append(addr, insertQ->values, table->row_size);
                break;
            case SELECT:;
                log_info("SELECT");
                selectQuery* selectQ = (selectQuery*) header;
                scan_ids(data_region,selectQ);
                break;
            default:;
                log_info("[Warning] cmd not recognized: %d with id %d",
                         header->cmd, header->id);
                break;
        }

        /*
        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        uint32_t info = msg->arg1;
        uchar* k_v    = msg->data;

        #ifdef DB_HASH_TABLE
            uint32_t hash = msg->arg2;
                                    //todo does not cover the whole range
                                    //of addresses of this core
            uint32_t words_offset = ((hash & 0x0007FFFF)
                                    % CORE_DATABASE_SIZE_WORDS);

            *addr = (address_t)&data_region[words_offset];
        #endif



        value_entry* value_entry_ptr;

        switch(msg->cmd_rc){
            case PUT:;
                log_info("PUT on address: %04x k_v: %s", *addr, k_v);

                put(addr, info, k_v, &k_v[k_size_from_info(info)]);

                revert_src_dest(msg);
                msg->cmd_rc = PUT_REPLY;

                spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                break;
            case PULL:;
                log_info("PULL on address: %04x k: %s", *addr, k_v);

                #ifdef DB_HASH_TABLE
                    value_entry_ptr = pull(*addr,       info, k_v);
                #else
                    value_entry_ptr = pull(data_region, info, k_v);
                #endif

                if(value_entry_ptr){

                    revert_src_dest(msg);

                    msg->cmd_rc = PULL_REPLY;

                    log_info("Replying PULL request id %d", msg->seq);
                    log_info("with data (s: %s) of type %d, size %d",
                             value_entry_ptr->data, value_entry_ptr->type,
                             value_entry_ptr->size);

                    msg->arg1 = to_info(0, 0,
                                        value_entry_ptr->type,
                                        value_entry_ptr->size);

                    memcpy(msg->data,
                           value_entry_ptr->data, value_entry_ptr->size);

                    msg->length = sizeof(sdp_hdr_t) + 16
                                  + value_entry_ptr->size;

                    print_msg(msg);

                    spin1_send_sdp_msg(msg, SDP_TIMEOUT);
                }
                else{
                    log_info("Not found...");

                    #ifdef DB_HASH_TABLE
                        msg->arg1 = 0; //failure
                        msg->length = sizeof(sdp_hdr_t) + 16;
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);
                    #endif
                }
                break;
            case SELECT_IDS:
                log_info("RECEIVED A SELECT_IDs");
                scan_ids(data_region);
                break;
            default:
                log_info("[Warning] cmd_rc not recognized: %d with id %d", msg->cmd_rc, msg->seq);
                break;
        }

        */

        // free the message to stop overload
        spin1_msg_free(msg);
    }
}

void c_main()
{
    chipx = spin1_get_chip_id() & 0xF0 >> 8;
    chipy = spin1_get_chip_id() & 0x0F;
    core  = spin1_get_core_id();

    log_info("Initializing Slave (%d,%d,%d)", chipx, chipy, core);

    table = (Table*)0x63e551a8; //todo hardcoded...

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    clear(data_region, CORE_DATABASE_SIZE_WORDS);

    addr = (address_t*)malloc(sizeof(address_t));
    *addr = data_region;

                                  //todo not hardcoded
    //entryQueue = (Entry*)sark_alloc(4, sizeof(Entry));

    // set timer tick value to 100ms
    spin1_set_timer_tick(TIMER_PERIOD);

    //recent_messages_queue   = init_double_linked_list();
    unacknowledged_replies  = init_double_linked_list();

    sdp_buffer = circular_buffer_initialize(100);

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, -1);
    spin1_callback_on(USER_EVENT,       process_requests,    1);
    spin1_callback_on(TIMER_TICK,       update,              2);

    simulation_run();
}