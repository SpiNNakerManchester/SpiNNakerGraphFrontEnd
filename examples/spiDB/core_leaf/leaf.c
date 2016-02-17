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
#include "pull.h"
#include "put.h"
#include "scan.h"

#define TIMER_PERIOD 100

//Globals
uint32_t time = 0;

static circular_buffer sdp_buffer;

uchar chipx, chipy, core;
uchar branch;

uint32_t myId;

Table* tables;

void update(uint ticks, uint b){
    use(ticks);
    use(b);

    time += TIMER_PERIOD;
}

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    sdp_msg_t* msg     = (sdp_msg_t*)mailbox;
    sdp_msg_t* msg_cpy = (sdp_msg_t*)sark_alloc(1,
                                sizeof(sdp_msg_t) + sizeof(insertEntryQuery));

    sark_word_cpy(msg_cpy, msg, sizeof(sdp_msg_t) + sizeof(insertEntryQuery));

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

address_t* addr;

uint32_t*  table_rows_in_this_core;
int*  table_max_row_id_in_this_core; //needs to be signed

address_t* table_base_addr;

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

sdp_msg_t* send_empty_response_to_host(spiDBcommand cmd, id_t id){
    sdp_msg_t* msg = create_sdp_header_to_host();

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = id;
    r->cmd = cmd;
    r->success = true;
    r->x = chipx;
    r->y = chipy;
    r->p = core;

    msg->length = sizeof(sdp_hdr_t) + sizeof(Response);

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send response to host");
        return NULL;
    }

    return msg;
}

sdp_msg_t* send_string_response_to_host(spiDBcommand cmd,
                                        id_t id,
                                        uchar* string){

    sdp_msg_t* msg = create_sdp_header_to_host();

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = id;
    r->cmd = cmd;
    r->success = true;
    r->x = chipx;
    r->y = chipy;
    r->p = core;

    msg->length = sizeof(sdp_hdr_t) + 9 + 16;

    sark_mem_cpy(&r->entry, string, 16);

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send response to host");
        return NULL;
    }

    return msg;
}

void process_requests(uint arg0, uint arg1){

    uint32_t mailbox;
    while(circular_buffer_get_next(sdp_buffer, &mailbox)){
        sdp_msg_t* msg = (sdp_msg_t*)mailbox;

        spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

        if(header->cmd == SELECT_RESPONSE){
            //gather responses

            selectResponse* selResp = (selectResponse*)header;
            log_info("seResponse on '%s' with addr %08x from core %d",
                     selResp->table->name, selResp->addr, get_srce_core(msg));
            breakInBlocks(selResp);

            continue;
        }

        #ifdef DB_TYPE_KEY_VALUE_STORE
            uint32_t info;
            uchar* k,v;

            switch(header->cmd){
                case PUT:;
                    log_info("PUT");
                    putQuery* putQ = (putQuery*) header;
                    log_info("  on address: %04x, k_v: %s", *addr, putQ->k_v);
                    info    = putQ->info;
                    k       = putQ->k_v;
                    v       = &putQ->k_v[k_size_from_info(info)];

                    put(addr, info, k, v);

                    send_empty_response_to_host(PUT, putQ->id);
                    break;
                case PULL:;
                    log_info("PULL");
                    pullQuery* pullQ = (pullQuery*) header;

                    info    = pullQ->info;
                    k       = pullQ->k;

                    value_entry* value_entry_ptr = pull(data_region, info, k);

                    if(value_entry_ptr){
                        log_info("Found: %s", value_entry_ptr->data);
                    }
                    else{
                        log_info("Not found...");
                    }
                    break;
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
                    //printEntry(&e);

                    log_info("  %s < (%s,%s)",
                             insertE->table_name, e.col_name, e.value);

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

                    send_string_response_to_host(INSERT_INTO,
                                                 insertE->id,
                                                 e.col_name);
                    break;
                default:;
                    log_info("[Warning] cmd not recognized: %d with id %d",
                             header->cmd, header->id);
                    break;
            }
        #endif

        // free the message to stop overload
        //spin1_msg_free(msg);
    }
}

void receive_data (uint key, uint payload)
{
    log_info("Received MC packet with key=%d, payload=%08x", key, payload);

    selectQuery* selQ = (selectQuery*) payload;

    if(selQ->cmd != SELECT){
        log_error("Unexpected MC packet with selQ->cmd == %d", selQ->cmd);
        return;
    }

    log_info("SELECT");

    uint32_t table_index = getTableIndex(tables, selQ->table_name);
    if(table_index == -1){
        log_error("  Unable to find table '%d'", selQ->table_name);
        return;
    }

    print_table(&tables[table_index]);

    log_info("with base address: %08x", (uint32_t)table_base_addr[table_index]);
    log_info("final addr: %08x", data_region + (uint32_t)table_base_addr[table_index]);

    scan_ids(&tables[table_index],
             data_region+(uint32_t)table_base_addr[table_index],
             selQ,
             table_rows_in_this_core[table_index]);
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

    log_info("Initializing Leaf (%d,%d,%d)\n", chipx, chipy, core);

    table_rows_in_this_core = (uint32_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                                    sizeof(uint32_t));
    table_max_row_id_in_this_core =
        (uint32_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                                    sizeof(uint32_t));

    table_base_addr = (address_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                             sizeof(address_t));

    address_t b = 0;
    for(uint i=0; i<DEFAULT_NUMBER_OF_TABLES; i++){
        table_rows_in_this_core[i] = 0;
        table_max_row_id_in_this_core[i] = -1;
        table_base_addr[i] = b;
        b += DEFAULT_TABLE_SIZE_WORDS;
    }

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    clear(data_region, CORE_DATABASE_SIZE_WORDS);

    addr = (address_t*)malloc(sizeof(address_t));
    *addr = data_region;

    vcpu_t *sark_virtual_processor_info = (vcpu_t*) SV_VCPU;
    address_t root_data_address =
        data_specification_get_region(DB_DATA_REGION,
                    (address_t)sark_virtual_processor_info[ROOT_CORE].user0);

    tables = (Table*)root_data_address;

    spin1_set_timer_tick(TIMER_PERIOD);

    sdp_buffer = circular_buffer_initialize(150);

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,        sdp_packet_callback, 0);
    spin1_callback_on(USER_EVENT,           process_requests,    2);
    spin1_callback_on(TIMER_TICK,           update,              2);

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data,        0);
    spin1_callback_on(MC_PACKET_RECEIVED,   receive_data_void,   0);

    simulation_run();
}