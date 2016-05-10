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
#include "../../common/db-typedefs.h"
#include "../../common/sdp_utils.h"
#include "../../common/timer2.h"
#include "pull.h"
#include "put.h"
#include "scan.h"

//! data region definitions
typedef enum regions_e {
    SYSTEM_REGION = 0, SDP_PORT_REGION=1, DB_DATA_REGION = 2
} regions_e;

//! callback priority levels
typedef enum callback_priority_e {
    SDP_MC_PRIORITY=0, TIMER_TICK_PRIORITY = 1, USER_EVENT_PRIORITY = 2
} callback_priority_e;

//! elements within the transmission region
typedef enum transmission_region_elements_e {
    HAS_KEY=0, KEY=1
} transmission_region_elements_e;

//! elements within the sdp region
typedef enum sdp_port_region_elements_e {
    SDP_PORT_POSITION=0
} sdp_port_region_elements_e;

//! \data region elements
typedef enum string_region_elements_e {
    DATA_REGION_SIZE=0
} string_region_elements_e;

//! memory stores
address_t system_region;
address_t data_region;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

// key data
uint32_t has_key = 0;
uint32_t key = 0;

// sdp port data
uint32_t sdp_port_num = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! hardcoded size of queues
static uint32_t QUEUE_SIZE = 100;

//Globals
static circular_buffer sdp_buffer;
static circular_buffer mc_buffer;

//! core identification data
static uint32_t chip_x;
static uint32_t chip_y;
static uint32_t core;

//! state machine bool
static bool processing_events = false;

//! ????????????
uchar branch;

//! copies of sdp messages received.
sdp_msg_t** msg_copies;

//! ????????????????
uint i = 0;
uint as = 0;
id_t  myId;

#ifdef DB_TYPE_RELATIONAL
    Table* tables;
    uint32_t*  table_rows_in_this_core;
    int*  table_max_row_id_in_this_core; //needs to be signed
    address_t* table_base_addr;

    void reset_leaf_globals(){
        address_t b = 0;
        for(uint i=0; i<DEFAULT_NUMBER_OF_TABLES; i++){
            table_rows_in_this_core[i] = 0;
            table_max_row_id_in_this_core[i] = -1;
            table_base_addr[i] = b;
            b += DEFAULT_TABLE_SIZE_WORDS;
        }
    }
#endif

void update(uint ticks, uint b){
    use(ticks);
    use(b);
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);
        return;
    }
}

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    i = (i+1)%QUEUE_SIZE;
    register sdp_msg_t* m = msg_copies[i];
    sark_word_cpy(m, (sdp_msg_t*)mailbox, sizeof(sdp_hdr_t)+256);
    spin1_msg_free((sdp_msg_t*)mailbox);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, (uint32_t)m)) {
        if (!processing_events) {
            processing_events = true;
            if(!spin1_trigger_user_event(0, 0)){
                log_error("Unable to trigger user event.");
            }
        }
    }
    else{
        log_error("Unable to add SDP packet to circular buffer.");
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
    return send_internal_data_response(chip_x, chip_y, branch,
                                       data, data_size_bytes);
}

#ifdef DB_TYPE_KEY_VALUE_STORE
bool pull_respond(pullQuery* pullQ){
    try(pullQ);

    pullValue* v = pull(data_region, pullQ->info, pullQ->k);

    if(v){
        //printPullValue(v);
        pullValueResponse* r = (pullValueResponse*)
                               sark_alloc(1, sizeof(pullValueResponse));
        r->id = pullQ->id;
        r->cmd = PULL_REPLY;
        sark_mem_cpy(&r->v, v, sizeof(pullValue));

        send_data_response_to_branch(r,
                                     sizeof(pullValueResponse_hdr) +
                                     sizeof(v->type) + sizeof(v->size) +
                                     sizeof(v->pad) + v->size + 3);

/*
                                     sizeof(pullValueResponse)

        send_xyp_data_response_to_host(pullQ,
                                       &r->v,
                                       sizeof(r->v.type)
                                          + sizeof(r->v.size)
                                          + sizeof(r->v.pad)
                                          + r->v.size + 3,
                                       chip_x,
                                       chip_y,
                                       core);
*/
        sark_free(r);
        sark_free(v);
    }
    //else if not found, ignore

    return true;
}
#endif

void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    uint32_t mailbox;
    uint32_t payload;
    do {
        if (circular_buffer_get_next(sdp_buffer, &mailbox)) {
            sdp_msg_t* msg = (sdp_msg_t*)mailbox;

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            if(!header){
                continue;
            }

            #ifdef DB_TYPE_KEY_VALUE_STORE
                info_t info;
                uchar* k,v;

                switch(header->cmd){
                    case PUT:;
                        //log_info("PUT");
                        putQuery* putQ = (putQuery*) header;
                        //log_info("  |- %08x  k_v: %s", *addr, putQ->k_v);

                        info    = putQ->info;
                        k       = putQ->k_v;
                        v       = (uchar*)&putQ->k_v[k_size_from_info(info)];

                        size_t bytes_written = put(data_region, info, k, v);

                        sdp_msg_t* respMsg = send_data_response_to_host(
                            putQ, &bytes_written, sizeof(size_t), chip_x,
                            chip_y, core);

                        sark_free(respMsg);
                        break;
                    #ifdef DB_SUBTYPE_HASH_TABLE
                    case PULL:;
                        log_info("PULL %d", ++as);
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

                        send_data_response_to_host(
                            insertE, e.col_name, 16, chip_y, chip_y, core);
                        break;
                    default:;
                        //log_info("[Warning] cmd not recognized: %d with id %d",
                        //         header->cmd, header->id);
                        break;
                }
            #endif

        }
        else if(circular_buffer_get_next(mc_buffer, &payload)){
            spiDBQueryHeader* header = (spiDBQueryHeader*)payload;

            switch(header->cmd){
                #ifdef DB_TYPE_RELATIONAL
                case SELECT:
                    log_info("SELECT");

                    selectQuery* selQ = (selectQuery*)payload;

                    uint32_t table_index = getTableIndex(tables, selQ->table_name);
                    if(table_index == -1){
                        log_error("  Unable to find table '%s'", selQ->table_name);
                        return;
                    }

                    scan_ids(&tables[table_index],
                             data_region+(uint32_t)table_base_addr[table_index],
                             selQ,
                             table_rows_in_this_core[table_index]);
                    break;
                #endif
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
        else {
            processing_events = false;
        }
    }while (processing_events);
}

void receive_MC_data(uint key, uint payload)
{
    use(key);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(mc_buffer, (uint32_t)payload)) {
        if (!processing_events) {
            processing_events = true;
            if(!spin1_trigger_user_event(0, 0)){
                log_error("Unable to trigger user event.");
            }
        }
    }
    else{
        log_error("Unable to add MC packet to circular buffer.");
    }

}

void receive_MC_void (uint key, uint unknown){
    use(key);
    use(unknown);
    log_error("Received unexpected MC packet with no payload.");
}

static bool initialize(uint32_t *timer_period) {
    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpecification address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read DataSpecification header");
        return false;
    }

    system_region = data_specification_get_region(SYSTEM_REGION, address);

    if (!simulation_read_timing_details(
            system_region, APPLICATION_NAME_HASH, timer_period)) {
        log_error("failed to read the system header");
        return false;
    }

    data_region = data_specification_get_region(DB_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    // clear the data region of any data
    uint32_t data_region_size = data_region[DATA_REGION_SIZE] / 4; // bytes to ints
    memory_utils_clear(data_region, data_region_size);

    address_t sdp_port_region =
        data_specification_get_region(SDP_PORT_REGION, address);
    sdp_port_num = sdp_port_region[SDP_PORT_POSITION];

        msg_copies = (sdp_msg_t**)sark_alloc(QUEUE_SIZE, sizeof(sdp_msg_t*));
    for(uint i = 0; i < QUEUE_SIZE; i++){
        msg_copies[i] = (sdp_msg_t*)sark_alloc(1, sizeof(sdp_hdr_t)+256);
    }

    if(!msg_copies){
        log_error("Unable to allocate memory for msg_copies");
        rt_error(RTE_SWERR);
    }

    log_info("Initialization completed successfully!");
    return true;
}

void c_main()
{
    chip_x = (spin1_get_chip_id() & 0xFF00) >> 8;
    chip_y = spin1_get_chip_id() & 0x00FF;
    core  = spin1_get_core_id();
    branch = getBranch();

    myId  = chip_x << 16 | chip_y << 8 | core;

    log_info("Initializing Leaf (%d,%d,%d)\n", chip_x, chip_y, core);

    // timer period
    uint32_t timer_period;

    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    #ifdef DB_TYPE_RELATIONAL

    table_rows_in_this_core = (uint32_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                                    sizeof(uint32_t));
    table_max_row_id_in_this_core =
        (uint32_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES, sizeof(uint32_t));

    table_base_addr = (address_t*)sark_alloc(DEFAULT_NUMBER_OF_TABLES,
                                             sizeof(address_t));

    reset_leaf_globals();


    vcpu_t *sark_virtual_processor_info = (vcpu_t*) SV_VCPU;

    //get the ROOT data address, which points to the table definitions
    tables = (Table*)data_specification_get_region(DB_DATA_REGION,
                    (address_t)sark_virtual_processor_info[ROOT_CORE].user0);

    log_info("Tables at %08x", tables);

    #endif

    msg_copies = (sdp_msg_t**)sark_alloc(QUEUE_SIZE, sizeof(sdp_msg_t*));
    for(uint i = 0; i < QUEUE_SIZE; i++){
        msg_copies[i] = (sdp_msg_t*)sark_alloc(1, sizeof(sdp_hdr_t)+256);
    }

    if(!msg_copies){
        log_error("Unable to allocate memory for msg_copies");
        rt_error(RTE_SWERR);
    }

    sdp_buffer = circular_buffer_initialize(QUEUE_SIZE);
    mc_buffer = circular_buffer_initialize(QUEUE_SIZE);

    if(!sdp_buffer || !mc_buffer){
        rt_error(RTE_SWERR);
    }

    log_info("Initialized sdp_buffer and mc_buffer");

    spin1_set_timer_tick(timer_period);

    // Set up callback listening to SDP messages
    simulation_register_simulation_sdp_callback(
        &simulation_ticks, &infinite_run, SDP_MC_PRIORITY);

    // register callbacks
    spin1_sdp_callback_on(sdp_port_num, sdp_packet_callback, SDP_MC_PRIORITY);
    spin1_callback_on(USER_EVENT, process_requests, USER_EVENT_PRIORITY);
    spin1_callback_on(TIMER_TICK, update, USER_EVENT_PRIORITY);

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_MC_data, SDP_MC_PRIORITY);
    spin1_callback_on(MC_PACKET_RECEIVED, receive_MC_void, SDP_MC_PRIORITY);

    simulation_run();
}