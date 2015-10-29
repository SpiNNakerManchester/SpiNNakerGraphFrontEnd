/****a* master.c/master_summary
*
* COPYRIGHT
*  Copyright (c) The University of Manchester, 2011. All rights reserved.
*  SpiNNaker Project
*  Advanced Processor Technologies Group
*  School of Computer Science
*  Author: Arthur Ceccotti
*******/

#define LOG_LEVEL 50 //TODO hmmm

#include "spin1_api.h"
#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "../sdram_writer.h"
#include "put.h"
#include "../sdp_utils.h"
#include <data_specification.h>
#include <debug.h>
#include <sark.h>

address_t* current;

sdp_msg_t send_sdp_PULL(uint8_t dest_core, uint32_t info, void* k){

    sdp_msg_t msg = create_sdp_header(dest_core);

    // ======================== SCP ========================
    msg.cmd_rc      = PULL; // TODO hmmm apparently cmd_rc is supposed to be used for something else
    msg.seq         = 1; // TODO error checking...

    msg.arg1        = info;
    msg.arg2        = *current;
    append(current, k,1); // Store into sdram and pass a pointer to it

    msg.length      = sizeof(sdp_hdr_t) + 16;

    spin1_send_sdp_msg(&msg, SDP_TIMEOUT); //message, timeout

    return msg;
}

core_dsg* core_dsgs;

core_dsg get_core_dsgs(uint32_t core_id) {

    // Get pointer to 1st virtual processor info struct in SRAM
    vcpu_t *sark_virtual_processor_info = (vcpu_t*) SV_VCPU;

    // Get the address this core's DTCM data starts at from the user data member
    // of the structure associated with this virtual processor
    address_t address = (address_t) sark_virtual_processor_info[core_id].user0;

    core_dsg dsg;

    address_t data_address = data_specification_get_region(DB_DATA_REGION, address);

    dsg.data_start      = (address_t*) sark_alloc(1, sizeof(address_t));
    dsg.data_current    = (address_t*) sark_alloc(1, sizeof(address_t));

    //dsg.system_address = data_specification_get_region(SYSTEM_REGION, address);
    *dsg.data_start     = data_address; //used to store size
    *dsg.data_current   = data_address+1;//start from next word

    return dsg;
}


#define FIRST_SLAVE 2
#define LAST_SLAVE  16

void master_pull(uint32_t k_info, void* k){
    log_info("Sending PULL broadcast");
    for(int i=FIRST_SLAVE; i<=LAST_SLAVE; i++){
        send_sdp_PULL(i, k_info, k);
    }
}

void print_core_infos(){
    for(int i=FIRST_SLAVE; i<=LAST_SLAVE; i++){
        log_info("core_dsg[%d].data_start = %08x", i, *core_dsgs[i].data_start);
    }
}

uint32_t p = 2;

bool round_robin_put(uint32_t info, void* k, void* v){

    bool success = put(core_dsgs[p++], info, k, v);

    if(p > LAST_SLAVE){ p = FIRST_SLAVE; }

    return success;
}

void update (uint ticks, uint b)
{
    // I give it a few ticks between reading and writing, just in case
    // the IO operations take a bit of time
    uint32_t zero = 0;
    uint32_t one = 1;
    uint32_t two = 2;
    uint32_t three = 3;

    //todo im giving them time to prepare..
    if(ticks == 100){
        //ignore 0,1 and 17
        for(int i=2; i<NUM_CPUS-1; i++){
            core_dsgs[i] = get_core_dsgs(i);
        }

        print_core_infos();
    }
    else if(ticks == 200){
        for(int i = 0; i < 100; i++){
            round_robin_put(to_info2(UINT32, UINT32, &i, &i), &i, &i);
        }
    }
    else if(ticks == 300){
        master_pull(to_info1(UINT32, &zero), &zero); //core 2
        master_pull(to_info1(UINT32, &one), &one); //core 3
        master_pull(to_info1(UINT32, &two), &two); //core 4
        master_pull(to_info1(UINT32, &three), &three); //core 5
    }
}

void sdp_packet_callback(uint mailbox, uint port) {

    use(port); // TODO is this wait for port to be free?
    sdp_msg_t* msg = (sdp_msg_t*) mailbox;

    switch(msg->cmd_rc){
        case PULL:; uint32_t info = msg->arg1;
                    void* v = msg->arg2; //pointer to the data from master

                    log_info("Core %d replied PULL with data = %d (%s)",
                             msg->srce_port & 0x1F, *((uint32_t*)v), (char*)v);

                    //send acknowledgement back!!!
                    break;
        default:
                    break;
    }

    // free the message to stop overload
    spin1_msg_free(msg);
}

void c_main()
{
    log_info("Initializing Master...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    core_dsgs = (core_dsg*) sark_alloc(NUM_CPUS, sizeof(core_dsg));

    current  = (address_t*) sark_alloc(1, sizeof(address_t));
    *current = data_region;

    // set timer tick value to 100ms
    spin1_set_timer_tick(100);

    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 0);
    spin1_callback_on (SDP_PACKET_RX, sdp_packet_callback, 1);

    simulation_run();
}