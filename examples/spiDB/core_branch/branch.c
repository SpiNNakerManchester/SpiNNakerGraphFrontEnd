/***** branch.c/branch_summary
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
#include "../sdp_utils.h"

#define TIMER_PERIOD 100
#define QUEUE_SIZE 128

//Globals
static circular_buffer sdp_buffer;

extern uchar chipx, chipy, core;
static bool processing_events = false;

id_t  myId;

#ifdef DB_TYPE_RELATIONAL
sdp_msg_t* send_response_msg(selectResponse* selResp,
                             uint32_t col_index){

    try(selResp);

    Table* table = selResp->table;
    id_t sel_id = selResp->id;
    address_t addr = selResp->addr;

    try(table && col_index > 0 && addr);

    uchar* col_name = table->cols[col_index].name;
    size_t data_size = table->cols[col_index].size;

    try(col_name && *col_name != 0 && data_size != 0);

    uchar pos = get_byte_pos(table, col_index) >> 2;

    sdp_msg_t* msg = create_sdp_header_to_host_alloc_extra(
                        sizeof(Response_hdr) + sizeof(Entry_hdr) + data_size);

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = sel_id;
    r->cmd = SELECT;
    r->success = true;
    r->x = chipx;
    r->y = chipy;
    r->p = core;

    Entry* e = (Entry*)&(r->data);
    e->row_id = myId << 24 | (uint32_t)addr;
    e->type   = table->cols[col_index].type;
    e->size   = (e->type == UINT32) ?
                 sizeof(uint32_t) : sark_str_len((char*)&addr[pos]);

    sark_word_cpy(e->col_name, col_name, MAX_COL_NAME_SIZE);
    sark_word_cpy(e->value, &addr[pos], e->size);

    log_info("Sending to host (%s,%s)", e->col_name, e->value);

    msg->length = sizeof(sdp_hdr_t) + sizeof(Response_hdr) +
                  sizeof(Entry_hdr) + e->size;

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send Response to host");
        return NULL;
    }

    return msg;
}

void breakInBlocks(selectResponse* selResp){

    if(selResp->n_cols == 0){ //wildcard '*'
        for(uchar i = 0; i < selResp->table->n_cols; i++){
            sdp_msg_t* msg = send_response_msg(selResp,i);
            if(!msg){
                log_info("Failed to send entry message...");
            }
            else{
                sark_delay_us(2);
                sark_free(msg);
            }
        }
    }
    else{ //columns specified
        for(uchar i = 0; i < selResp->n_cols; i++){
            sdp_msg_t* msg = send_response_msg(selResp,selResp->col_indices[i]);

            if(!msg){
                log_info("Failed to send entry message...");
            }
            else{
                sark_delay_us(2);
                sark_free(msg);
            }
        }
    }
}
#endif


void update(uint ticks, uint b){
    use(ticks);
    use(b);
}


sdp_msg_t** msg_cpies;
uint i = 0;

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    i = (i+1)%QUEUE_SIZE;
    register sdp_msg_t* m = msg_cpies[i];
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

void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    uint32_t mailbox;
    uint i = 0;
    do {
        if (circular_buffer_get_next(sdp_buffer, &mailbox)) {
            if(++i > 1){
                log_info("i is %d", i);
            }

            sdp_msg_t* msg = (sdp_msg_t*)mailbox;

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            #ifdef DB_TYPE_KEY_VALUE_STORE
                switch(header->cmd){
                    case PULL_REPLY:;
                        log_info("PULL_REPLY");
                        pullValueResponse* r = (pullValueResponse*)header;

                        r->cmd = PULL;

                        send_xyp_data_response_to_host(header,
                                                       &r->v,
                                                       sizeof(r->v.type)
                                                          + sizeof(r->v.size)
                                                          + sizeof(r->v.pad)
                                                          + r->v.size + 3,
                                                       get_srce_chip_x(msg),
                                                       get_srce_chip_y(msg),
                                                       get_srce_core(msg));
                        break;
                    default:;
                        break;
                }
            #endif
            #ifdef DB_TYPE_RELATIONAL
                switch(header->cmd){
                    case SELECT_RESPONSE:;
                        selectResponse* selResp = (selectResponse*)header;
                        log_info("SELECT_RESPONSE on '%s' with addr %08x from core %d",
                                 selResp->table->name, selResp->addr, get_srce_core(msg));
                        breakInBlocks(selResp);
                        break;
                    default:;
                        //log_info("[Warning] cmd not recognized: %d with id %d",
                        //         header->cmd, header->id);
                        break;
                }
            #endif
        }
        else {
            processing_events = false;
        }
    }while (processing_events);
}

void receive_MC_data(uint key, uint payload)
{
    use(key);
    use(payload);
    log_error("Received unexpected MC packet with key=%d, payload=%08x",
              key, payload);
}

void receive_MC_void (uint key, uint unknown){
    use(key);
    use(unknown);
    log_error("Received unexpected MC packet with key=%d, no payload", key);
}

void c_main()
{
    chipx = (spin1_get_chip_id() & 0xFF00) >> 8;
    chipy = spin1_get_chip_id() & 0x00FF;
    core  = spin1_get_core_id();

    myId  = chipx << 16 | chipy << 8 | core;

    log_info("Initializing Branch (%d,%d,%d)\n", chipx, chipy, core);

    msg_cpies = (sdp_msg_t**)sark_alloc(QUEUE_SIZE, sizeof(sdp_msg_t*));
    for(uint i = 0; i < QUEUE_SIZE; i++){
        msg_cpies[i] = (sdp_msg_t*)sark_alloc(1, sizeof(sdp_hdr_t)+256);
    }

    if(!msg_cpies){
        log_error("Unable to allocate memory for msg_cpies");
        rt_error(RTE_SWERR);
    }

    sdp_buffer = circular_buffer_initialize(QUEUE_SIZE);

    if(!sdp_buffer){
        rt_error(RTE_SWERR);
    }

    spin1_set_timer_tick(TIMER_PERIOD);

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,        sdp_packet_callback, 0);
    spin1_callback_on(USER_EVENT,           process_requests,    2);
    spin1_callback_on(TIMER_TICK,           update,              2);

    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_MC_data,     0);
    spin1_callback_on(MC_PACKET_RECEIVED,   receive_MC_void,     0);

    simulation_run();
}