/****a* master.c/master_summary
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
#include "recording.h"
#include "../db-typedefs.h"
#include <data_specification.h>
#include <debug.h>

#define SDP_PORT    3
#define SDP_TIMEOUT 1

sdp_msg_t put_sdp_msg(void* k, var_type k_type, void* v, var_type v_type){

/*
  struct sdp_msg *next;		//!< Next in free list
  ushort length;		//!< length
  ushort checksum;		//!< checksum (if used)

  // sdp_hdr_t (mandatory)

  uchar flags;			//!< Flag byte
  uchar tag;			//!< IP tag
  uchar dest_port;		//!< Destination port/CPU
  uchar srce_port;		//!< Source port/CPU
  ushort dest_addr;		//!< Destination address
  ushort srce_addr;		//!< Source address

  // cmd_hdr_t (optional)

  ushort cmd_rc;		//!< Command/Return Code
  ushort seq;			//!< Sequence number
  uint arg1;			//!< Arg 1
  uint arg2;			//!< Arg 2
  uint arg3;			//!< Arg 3


  // user data (optional)

  uchar data[SDP_BUF_SIZE];	//!< User data (256 bytes)

  uint __PAD1;			//!< Private padding
*/

    uint32_t k_size = get_size_bytes(k,k_type);
    uint32_t v_size = get_size_bytes(v,v_type);

    uint32_t k_type_and_size = k_size | ((k_type) << 28);
    uint32_t v_type_and_size = v_size | ((v_type) << 28);

    sdp_msg_t msg;

    // ===================== SDP Header =====================
    msg.flags       = 0x07; // No reply required
    msg.tag         = 0; // 0 = Send internally (not over the Ethernet)

    msg.dest_addr   = spin1_get_chip_id(); // Destination core is on the same chip
    msg.dest_port   = (SDP_PORT << PORT_SHIFT) | 2; // TODO should not be hardcoded

    msg.srce_addr   = spin1_get_chip_id();
    msg.srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    // ======================== SCP ========================
    msg.cmd_rc      = PUT; // Command
    msg.seq         = 1; // TODO error checking...

    msg.arg1        = k_type_and_size; // Arg1 tells the type (eg. STRING, INT, etc.) of the key
    msg.arg2        = v_type_and_size; // Arg2 tells the type (eg. STRING, INT, etc.) of the value
    msg.arg3        = 0; // Unused

    // TODO for now only Key and Value as integers
    //TODO hmmmm ok. For some reason this doesn't work properly!!!!!!!!!!!!!!!!!!1
    msg.data[0]     = *((uint32_t*)k);
    msg.data[1]     = 0;
    msg.data[2]     = 0;
    msg.data[3]     = 0; //TODO !!!!!!!! REALLY SHOULD DO WORD->ARR OF BYTES
    msg.data[4]     = *((uint32_t*)v);
    msg.data[5]     = 0;
    msg.data[6]     = 0;
    msg.data[7]     = 0; //TODO same here...

    msg.length      = sizeof(sdp_hdr_t) + 16 + k_size + v_size;

    return msg;
}

void send_packet(void) {
    log_info("Sending packet...");

    uint32_t a = 10;
    uint32_t b = 16;
    sdp_msg_t put_msg = put_sdp_msg(&a, UINT32, &b, UINT32);

    print_msg(put_msg);

    spin1_send_sdp_msg(&put_msg, SDP_TIMEOUT); //message, timeout
}

void update (uint ticks, uint b)
{
    // I give it a few ticks between reading and writing, just in case
    // the IO operations take a bit of time
    if(ticks == 1000)          { send_packet(); }
}

void sdp_packet_callback(uint mailbox, uint port) {
    log_info("Received a packet!!!!!!!!!!!!!!!!!!!!!!!!");
    //TODO implement packets coming from ethernet or monitor cores from another chip
}

void c_main()
{
    log_info("Initializing Master...");

    // set timer tick value to 100ms
    spin1_set_timer_tick(100);

    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 0);
    spin1_callback_on (SDP_PACKET_RX, sdp_packet_callback, 1);

    simulation_run();
}