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
#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "put.h"
#include "pull.h"

//#include <bit_field.h>

#include <debug.h>
#include "put_tests.c"
#include "pull_tests.c"

/*void clear_entries(){
    recording_channel_t* recording_channel = &g_recording_channels[channel];

    /*//*recording_channel->current = 0;

    clear_bit_field((bit_field_t)recording_channel->current, bytes_written);
}*/

static bool initialize() {

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpec data address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read Dataspec header");
        return false;
    }

    address_t system_region = data_specification_get_region(SYSTEM_REGION, address);
    address_t data_region   = data_specification_get_region(STRING_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    uint32_t data_region_size = 500;

    recording_init(data_region, data_region_size);

                                               // TODO should make my own channel
    //if (!recording_initialse_channel(data_region, e_recording_channel_spike_history, data_region_size)) {
    //    log_error("Could not initialize channel.");
    //    return false;
    //}

    log_info("Initialization completed successfully!");
    return true;
}

void update (uint ticks, uint b)
{

    // I give it a few ticks between reading and writing, just in case
    // the IO operations take a bit of time
    if(ticks == 100){
        //run_put_tests();
        run_pull_tests();
        //log_info("infoinggggg:");
        //put(STRING, STRING, "I love","Spinnaker");

    /*
      uint32_t one = 1;
      uint32_t a = 10;
      uint32_t b = 16;
      put(&one, UINT32, &one, UINT32);
      put("I love", STRING, "Spinnaker", STRING);
      put(&a, UINT32, "hahaz", STRING);
      put("ah", STRING, &b, UINT32);
      put("yo", STRING, "boy", STRING);
      put("I like cheese, man", STRING, "but do you?", STRING);

      log_info("We wrote a total of %d bytes", bytes_written);
      */
    }
    else if(ticks == -2)   {}
         //log_info("Hello -> %s", pull("Hello",STRING));
         //uint32_t k = 10;
         //var_type k_type = UINT32;
         //value v = pull(&k,k_type);

         /*
         char* k = "yo";
         var_type k_type = STRING;
         value_ v = pull(k_type, k);

        switch(k_type){
            case STRING: log_inrecording_channelfo("STRING Key %s", k);
                         break;
            case UINT32: log_info("UINT32 Key %d", k);
                         break;
        }

        switch(v.type){
            case STRING: log_info("has value -> %s (type: STRING, size: %d)", v.data, v.size);
                         break;
            case UINT32: log_info("has value -> %d (type: UINT32, size: %d)", *((uint32_t*)v.data), v.size);
                         break;
            case NUL:
            default:     log_info("was not found!");
                         break;
        }

    }
    */
    //else if(ticks == 300)   { recording_finalise();
    //                          spin1_exit(0);}
}


void sdp_packet_callback(uint mailbox, uint port) {
    log_info("Received a packet...");

    use(port); // TODO is this wait for port to be free?
    sdp_msg_t* msg = (sdp_msg_t*) mailbox;

    print_msg(*msg);

    uint k_type_and_size = msg->arg1;
    uint v_type_and_size = msg->arg2;

    uchar k = msg->data[0]; //TODO !!!!!!!! REALLY SHOULD DO WORD->ARR OF BYTES
    uchar v = msg->data[4]; //TODO same here...

    switch(msg->cmd_rc){
        case PUT: put(k_type_and_size,v_type_and_size, &k, &v);
                  break;
        default:
                 break;
    }

    // free the message to stop overload
    spin1_msg_free(msg);
}

void c_main()
{
    log_info("Initializing Slave...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }
    // set timer tick value to 100ms
    spin1_set_timer_tick(100);


    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 0); //TODO ENABLE WITH SOMETHING ELSE...
    //spin1_callback_on(SDP_PACKET_RX,        sdp_packet_callback, 1);
    //spin1_callback_on(MC_PACKET_RECEIVED,   sdp_packet_callback, 1);
    //spin1_callback_on(MCPL_PACKET_RECEIVED, sdp_packet_callback, 1);

    simulation_run();
}