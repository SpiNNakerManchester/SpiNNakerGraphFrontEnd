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

static circular_buffer sdp_buffer;

uchar chipx;
uchar chipy;
uchar core;
uchar branch;

uint32_t myId;

Table* table;

sdp_msg_t msg;

void update(uint ticks, uint b){
    use(ticks);
    use(b);

    time += TIMER_PERIOD;

    if(ticks == 10){
         // Get pointer to 1st virtual processor info struct in SRAM
        /*
        vcpu_t *sark_virtual_processor_info = (vcpu_t*) SV_VCPU;
        address_t address = (address_t) sark_virtual_processor_info[ROOT_CORE].user0;
        address_t root_data_address = data_specification_get_region(DB_DATA_REGION, address);
        table = (Table*)root_data_address;
        */

        print_table(table);
    }

/*    if(time == 5000000){

    }*/
}


uint32_t entriesInQueue = 0;
uchar* entryQueue;//TODO 2-D array. Todo HARDCODED

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    if (circular_buffer_add(sdp_buffer, mailbox)) {
        if(!spin1_trigger_user_event(0, 0)){
          log_error("Unable to trigger user event.");
        }
    }
}

address_t* addr;

uint32_t rows_in_this_core = 0;

uchar getBranch(){
  switch(core){
    case 5:
    case 6:
    case 7:
    case 8:
      return 2;
    case 9:
    case 10:
    case 11:
    case 12:
      return 3;
    case 13:
    case 14:
    case 15:
    case 16:
      return 4;
    default:
      return -1;
  }
}


sdp_msg_t* send_insert_into_response(uint32_t ins_id){
    /*
    typedef struct Entry{
        uint32_t row_id;
        uchar    col_name[16];
        size_t   size;
        uchar    value[256];
    } Entry;
    */

    sdp_msg_t* msg = create_sdp_header_to_host();

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = ins_id;
    r->cmd = INSERT_INTO;
    r->success = true;
    r->x = chipx;
    r->y = chipy;
    r->p = core;

    msg->length = sizeof(sdp_hdr_t) + sizeof(Response);//todo response hrd

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send INSERT_INTO Response to host");
    }

    return msg;
}

void process_requests(uint arg0, uint arg1){

    uint32_t mailbox;
    while(circular_buffer_get_next(sdp_buffer, &mailbox)){

        sdp_msg_t* msg = (sdp_msg_t*)mailbox;

        //log_info("Received message");
        //print_msg(msg);
        //spin1_msg_free(msg);

        spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

        if(header->cmd == SELECT_RESPONSE){
            //gather responses

            selectResponse* selResp = (selectResponse*)header;
            log_info("Received SELECT_RESPONSE with addr %08x", selResp->addr);
            breakInBlocks(selResp->id, selResp->addr);
            return;
        }

        #ifdef DB_TYPE_KEY_VALUE_STORE
            uint32_t info;
            uchar* k,v;

            switch(header->cmd){
                case PUT:;
                    log_info("PUT");
                    putQuery* putQ = (putQuery*) header;
                    //log_info("PUT on address: %04x k_v: %s", *addr, k_v);
                    info    = putQ->info;
                    k       = putQ->k_v;
                    v       = &k_v[k_size_from_info(info)]

                    put(addr, info, k, v);
                    break;
                case PULL:;
                    log_info("PULL");
                    pullQuery* pullQ = (pullQuery*) header;

                    info    = pullQ->info;
                    k       = pullQ->k_v;

                    value_entry* value_entry_ptr = pull(data_region, info, k);

                    if(value_entry_ptr){
                        log_info("Found: %s", value_entry_ptr->data);
                    }
                    else{
                        log_info("Not found...");
                    }
                    break;
                default:;
                    //log_info("[Warning] cmd not recognized: %d with id %d",
                    //         header->cmd, header->id);
                    break;
            }
        #endif
        #ifdef DB_TYPE_RELATIONAL
            switch(header->cmd){
                case INSERT_INTO:;
                    insertEntryQuery* insertE = (insertEntryQuery*) header;
                    Entry e = insertE->e;
                    //printEntry(&e);

                    log_info("INSERT_INTO (%s,%s) of size %d",
                             e.col_name, e.value, e.size);

                    uint32_t i = get_col_index(e.col_name);
                    uint32_t p = get_byte_pos(i); //todo very inefficient

                    //log_info("Col index is %d with pos %d. e.value is %s or e.size %d", i, p, e.value, e.size);

                    //todo double check that it is in fact empty (NULL)
                    memcpy(&entryQueue[p], e.value, e.size);

                    entriesInQueue++;

                    if(entriesInQueue == table->n_cols){//todo

                        address_t address_to_write = data_region + ((table->row_size * rows_in_this_core) + 3) / 4;

                        log_info("Flushing to address %08x", address_to_write);

                        rows_in_this_core++;

                        table->current_n_rows++; //todo concurrency!!!!! do I even need this?
                        entriesInQueue = 0; //reset and null all of them

                        memcpy(address_to_write,entryQueue,table->row_size);

                        for(uint32_t i = 0; i < table->row_size; i++){
                            //log_info("entryQueue[%d] = %c (%02x)", i, entryQueue[i], entryQueue[i]);
                            entryQueue[i] = 0;
                        }

                        send_insert_into_response(insertE->id);

                    }

                    //log_info("all %08x", data_region + (table->row_size * (e.row_id-1) + get_byte_pos(e.col_index) + 3) / 4);

                                                                    //-1 because the row_id starts from 1
                    //write(address_to_write,
                    //      insertE->e.value,
                    //      insertE->e.size); //assumes row_ids are 1,2,3,4,... single core TODO

                    //append(addr, insertQ->values, table->row_size);
                    break;
                default:;
                    log_info("[Warning] cmd not recognized: %d with id %d",
                             header->cmd, header->id);
                    break;
            }
        #endif

        // free the message to stop overload
        //spin1_msg_free(msg);

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
        }

        */

    }
}

void receive_data (uint key, uint payload)
{
    log_info("Received MC packet with key=%d, payload=%d", key, payload);

    selectQuery* selQ = (selectQuery*) payload;

    if(selQ->cmd != SELECT){
        log_error("Unexpected MC packet with selQ->cmd == %d", selQ->cmd);
        return;
    }

    log_info("SELECT");
    scan_ids(data_region,selQ);
}

void receive_data_void (uint key, uint unknown){
    use(key);
    use(unknown);
    log_error("Received unexpected MC packet with no payload.");
}

void c_main()
{
    chipx = spin1_get_chip_id() & 0xF0 >> 8;
    chipy = spin1_get_chip_id() & 0x0F;
    core  = spin1_get_core_id();
    branch = getBranch();

    myId  = chipx << 16 | chipy << 8 | core;

    log_info("Initializing Leaf (%d,%d,%d)", chipx, chipy, core);

    //table = (Table*)0x63e551a8; //todo hardcoded...

    //entryQueue = (uchar*)sark_alloc(table->row_size,sizeof(uchar)); //TODO should prob. be somewhere else
    entryQueue = (uchar*)sark_alloc(1024,sizeof(uchar)); //TODO should prob. be somewhere else
    for(uint32_t i = 0; i < 1024; i++){
        entryQueue[i] = 0;
    }

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    clear(data_region, CORE_DATABASE_SIZE_WORDS);

    addr = (address_t*)malloc(sizeof(address_t));
    *addr = data_region;

    table = (Table*) 0x637a8120;

                                  //todo not hardcoded
    //entryQueue = (Entry*)sark_alloc(4, sizeof(Entry));

    //recent_messages_queue   = init_double_linked_list();
    //unacknowledged_replies  = init_double_linked_list();

    spin1_set_timer_tick(TIMER_PERIOD);

    sdp_buffer = circular_buffer_initialize(100);

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,        sdp_packet_callback, 0);
    spin1_callback_on(USER_EVENT,           process_requests,    1);
    spin1_callback_on(TIMER_TICK,           update,              2);

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data,        0);
    spin1_callback_on(MC_PACKET_RECEIVED,   receive_data_void,   0);

    simulation_run();
    //spin1_start (SYNC_NOWAIT);
}