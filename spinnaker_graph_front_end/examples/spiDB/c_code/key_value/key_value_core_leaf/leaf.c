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
#include "key_value_commands.h"

//! data region definitions
typedef enum regions_e {
    SYSTEM_REGION = 0, SDP_PORT_REGION=1, BRANCH_REGION=2, DB_DATA_REGION = 3
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

//! elements within the sdp region
typedef enum branch_memory_region_elements_e {
    BRANCH_PROCESSOR=0
} branch_memory_region_elements_e;

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

//! processor id for where to send sdp packets for MST.
uchar branch_processor;

//! copies of sdp messages received.
sdp_msg_t** msg_copies;

//! ????????????????
uint i = 0;
uint as = 0;
id_t  myId;

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

    log_info("recieved sdp packet");
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

sdp_msg_t* send_data_response_to_branch(void* data,
                                        size_t data_size_bytes){
    log_info("sending pull response to %d", branch_processor);
    return send_internal_data_response(chip_x, chip_y, branch_processor,
                                       data, data_size_bytes);
}

bool pull_respond(pullQuery* pullQ){
    try(pullQ);

    pullValue* v = key_value_commands_pull(data_region, pullQ->info, pullQ->k);

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
    else{
        log_info("didnt find it");
    }
    //else if not found, ignore

    return true;
}

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

                    size_t bytes_written =
                        key_value_commands_put(data_region, info, k, v);

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
        }
        else if(circular_buffer_get_next(mc_buffer, &payload)){
            spiDBQueryHeader* header = (spiDBQueryHeader*)payload;

            switch(header->cmd){
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

    log_info("recieved packey with key %d, payload %d", key, payload);
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

    // get system region data
    system_region = data_specification_get_region(SYSTEM_REGION, address);
    if (!simulation_read_timing_details(
            system_region, APPLICATION_NAME_HASH, timer_period)) {
        log_error("failed to read the system header");
        return false;
    }

    // acquire brnach processor if needed
    address_t branch_region =
        data_specification_get_region(BRANCH_REGION, address);
    branch_processor = branch_region[BRANCH_PROCESSOR];

    // locate data region
    data_region = data_specification_get_region(DB_DATA_REGION, address);
    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    // clear the data region of any data
    uint32_t data_region_size = data_region[DATA_REGION_SIZE] / 4; // bytes to ints
    memory_utils_clear(data_region, data_region_size);

    // get sdp region data
    address_t sdp_port_region =
        data_specification_get_region(SDP_PORT_REGION, address);
    sdp_port_num = sdp_port_region[SDP_PORT_POSITION];
    log_info("sdp port num is %d", sdp_port_num);

    // build buffer of sdp messages
    msg_copies = (sdp_msg_t**)sark_alloc(QUEUE_SIZE, sizeof(sdp_msg_t*));
    for(uint i = 0; i < QUEUE_SIZE; i++){
        msg_copies[i] = (sdp_msg_t*)sark_alloc(1, sizeof(sdp_hdr_t)+256);
    }

    // if failed to allocate memory for buffer, crash
    if(!msg_copies){
        log_error("Unable to allocate memory for msg_copies");
        rt_error(RTE_SWERR);
    }

    // report that init was successful to iobuf
    log_info("Initialization completed successfully!");
    return true;
}

void c_main()
{
    // processor ids
    chip_x = (spin1_get_chip_id() & 0xFF00) >> 8;
    chip_y = spin1_get_chip_id() & 0x00FF;
    core  = spin1_get_core_id();
    myId  = chip_x << 16 | chip_y << 8 | core;

    log_info("Initializing Leaf (%d,%d,%d)\n", chip_x, chip_y, core);

    // timer period
    uint32_t timer_period;

    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // build some queues????? (why when youve built a buffer list????
    sdp_buffer = circular_buffer_initialize(QUEUE_SIZE);
    mc_buffer = circular_buffer_initialize(QUEUE_SIZE);

    if(!sdp_buffer || !mc_buffer){
        rt_error(RTE_SWERR);
    }

    // set up timer period
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