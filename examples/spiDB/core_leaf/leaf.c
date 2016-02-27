/***** leaf.c/leaf_summary
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
#include "../timer2.h"
#include "pull.h"
#include "put.h"
#include "scan.h"

#define TIMER_PERIOD 100

//Globals
static circular_buffer sdp_buffer;

extern uchar chipx, chipy, core;

uchar branch;

id_t  myId;

Table* tables;

address_t* addr;

uint32_t*  table_rows_in_this_core;
int*  table_max_row_id_in_this_core; //needs to be signed
address_t* table_base_addr;

void update(uint ticks, uint b){
    use(ticks);
    use(b);

    if(ticks == 0){
        START_TIMER();
    }

}

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    sdp_msg_t* msg     = (sdp_msg_t*)mailbox;
    sdp_msg_t* msg_cpy = (sdp_msg_t*)sark_alloc(1,
                          sizeof(sdp_hdr_t) + 256);

    sark_word_cpy(msg_cpy, msg, sizeof(sdp_hdr_t) + 256);

    spin1_msg_free(msg);

    if (circular_buffer_add(sdp_buffer, msg_cpy)){
        if(!spin1_trigger_user_event(0, 0)){
          log_error("Unable to trigger user event.");
          //sark_delay_us(1);
        }
    }
    else{
        log_error("Unable to add msg_cpy to SDP circular buffer");
    }
}

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

sdp_msg_t* send_data_response_to_branch(void* data,
                                        size_t data_size_bytes){
    return send_internal_data_response(chipx, chipy, branch,
                                       data, data_size_bytes);
}

pullValue* pull_respond(pullQuery* pullQ){

    pullValue* v = pull(data_region, pullQ->info, pullQ->k);

    if(v){
        printPullValue(v);
        /*
        send_data_response_to_host(PULL,
                                   pullQ->id,
                                   v,
                                   sizeof(v->type) + sizeof(v->size)
                                   + sizeof(v->pad) + v->size + 3);
        */

        pullValueResponse* r = (pullValueResponse*)
                               sark_alloc(1, sizeof(pullValueResponse));
        r->id = pullQ->id;
        r->cmd = PULL_REPLY;
        sark_mem_cpy(&r->v, v, sizeof(pullValue));

        send_data_response_to_branch(r,
                                     sizeof(pullValueResponse_hdr) +
                                     sizeof(v->type) + sizeof(v->size) +
                                     sizeof(v->pad) + v->size + 3);

        sark_free(r);
    }
    else{
        //log_info("Not found");
    }

    return v;
}

void process_requests(uint arg0, uint arg1){

    uint32_t mailbox;
    while(circular_buffer_get_next(sdp_buffer, &mailbox)){
        sdp_msg_t* msg = (sdp_msg_t*)mailbox;

        spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

        #ifdef DB_TYPE_KEY_VALUE_STORE
            uint32_t info;
            uchar* k,v;

            switch(header->cmd){
                case PUT:;
                    log_info("PUT");
                    putQuery* putQ = (putQuery*) header;
                    //log_info("  |- %08x  k_v: %s", *addr, putQ->k_v);

                    info    = putQ->info;
                    k       = putQ->k_v;
                    v       = &putQ->k_v[k_size_from_info(info)];

                    size_t bytes_written = put(addr, info, k, v);
                    log_info("data_region >> %08x", data_region);
                    log_info("addr >> %08x", *addr);
                    log_info("diff >> %08x", ((uint32_t)*addr)-(uint32_t)data_region);

                    send_data_response_to_host(putQ,
                                               &bytes_written, sizeof(size_t));
                    break;
                #ifdef DB_SUBTYPE_HASH_TABLE
                case PULL:;
                    log_info("PULL");
                    pull_respond((pullQuery*)header);
                    break;
                #endif
                default:;
                    break;
            }
        #endif
        #ifdef DB_TYPE_RELATIONAL
            switch(header->cmd){
                case INSERT_INTO:;
                    log_info("INSERT_INTO");

                    insertEntryQuery* insertE = (insertEntryQuery*) header;

                    uint32_t table_index = getTableIndex(tables,
                                                         insertE->table_name);

                    if(table_index == -1){
                        log_error("Unable to find table of name '%s' in tables");
                        return;
                    }

                    Table* t = &tables[table_index];
                    Entry e = insertE->e;

                    if(e.type == UINT32){
                        log_info("  %s < (%s, %d) (integer)",
                             insertE->table_name, e.col_name, *e.value);
                    }
                    else{
                    log_info("  %s < (%s, %s) (varchar)",
                             insertE->table_name, e.col_name, e.value);
                    }

                    uint32_t i = get_col_index(tables, e.col_name);
                    uint32_t p = get_byte_pos(tables, i);

                    //todo problem if packets interleave...
                    //needs to be signed, as table_max_row_id_in_this_core
                    //initializes to -1 (otherwise calculated as 0xFFFFFFFF)
                    if((int)e.row_id > table_max_row_id_in_this_core[table_index]){
                        table_rows_in_this_core[table_index]++;
                        table_max_row_id_in_this_core[table_index] = e.row_id;
                    }

                    uint32_t table_offset_words   = (uint32_t)table_base_addr[table_index];
                    uint32_t new_row_offset_words = ((t->row_size * (table_rows_in_this_core[table_index]-1)) + 3) >> 2;
                    uint32_t column_offset_words  = p >> 2;

                    address_t address_to_write = data_region +
                                                 table_offset_words +
                                                 new_row_offset_words +
                                                 column_offset_words;

                    log_info("  |- %08x (base: %08x)",
                             address_to_write,
                             data_region+(uint32_t)table_base_addr[table_index]);

                    sark_mem_cpy(address_to_write, e.value, e.size);

                    send_data_response_to_host(insertE,
                                               e.col_name,
                                               16);
                    break;
                default:;
                    //log_info("[Warning] cmd not recognized: %d with id %d",
                    //         header->cmd, header->id);
                    break;
            }
        #endif

        // free the message to stop overload
        //spin1_msg_free(msg);
        sark_free(msg);
    }
}

void receive_MC_data(uint key, uint payload)
{
    //log_info("Received MC packet with key=%d, payload=%08x", key, payload);

    spiDBQueryHeader* header = (spiDBQueryHeader*)payload;

    switch(header->cmd){
        /*
        case CLEAR:
            log_info("CLEAR");

            clear(data_region, CORE_DATABASE_SIZE_WORDS);
            resetLeafGlobals();
            *addr = data_region;

            break;
        */
        case SELECT:
            log_info("SELECT");

            selectQuery* selQ = (selectQuery*)payload;

            uint32_t table_index = getTableIndex(tables, selQ->table_name);
            if(table_index == -1){
                log_error("  Unable to find table '%d'", selQ->table_name);
                return;
            }

            scan_ids(&tables[table_index],
                     data_region+(uint32_t)table_base_addr[table_index],
                     selQ,
                     table_rows_in_this_core[table_index]);
            break;
        #ifndef DB_SUBTYPE_HASH_TABLE
        case PULL:
            log_info("PULL");
            pull_respond((pullQuery*)header);
            break;
        #endif
        default:
            log_error("Invalid MC command %d. Payload: %08x",
                      header->cmd, payload);
            break;
    }
}

void receive_MC_void (uint key, uint unknown){
    use(key);
    use(unknown);
    log_error("Received unexpected MC packet with no payload.");
}

void resetLeafGlobals(){
    address_t b = 0;
    for(uint i=0; i<DEFAULT_NUMBER_OF_TABLES; i++){
        table_rows_in_this_core[i] = 0;
        table_max_row_id_in_this_core[i] = -1;
        table_base_addr[i] = b;
        b += DEFAULT_TABLE_SIZE_WORDS;
    }
}

void c_main()
{
    chipx = (spin1_get_chip_id() & 0xFF00) >> 8;
    chipy = spin1_get_chip_id() & 0x00FF;
    core  = spin1_get_core_id();
    branch = getBranch();

    myId  = chipx << 16 | chipy << 8 | core;

    log_info("Initializing Leaf (%d,%d,%d)\n", chipx, chipy, core);

    table_rows_in_this_core = (uint32_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                                    sizeof(uint32_t));
    table_max_row_id_in_this_core =
        (uint32_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                                    sizeof(uint32_t));

    table_base_addr = (address_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                             sizeof(address_t));

    resetLeafGlobals();

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    addr = (address_t*)malloc(sizeof(address_t));
    *addr = data_region;

    vcpu_t *sark_virtual_processor_info = (vcpu_t*) SV_VCPU;

    //get the ROOT data address, which points to the table definitions
    tables = (Table*)data_specification_get_region(DB_DATA_REGION,
                    (address_t)sark_virtual_processor_info[ROOT_CORE].user0);

    spin1_set_timer_tick(TIMER_PERIOD);

    sdp_buffer = circular_buffer_initialize(150);

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,        sdp_packet_callback, 0);
    spin1_callback_on(USER_EVENT,           process_requests,    2);
    spin1_callback_on(TIMER_TICK,           update,              2);

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_MC_data,     0);
    spin1_callback_on(MC_PACKET_RECEIVED,   receive_MC_void,     0);

    ENABLE_TIMER ();	// Enable timer (once)

    simulation_run();
}