#include "spin1_api.h"
#include "common-typedefs.h"
#include "db-typedefs.h"

//todo hmmmmmm
#define SDP_PORT    3
#define SDP_TIMEOUT 1

sdp_msg_t create_sdp_header(uint8_t dest_core){
    sdp_msg_t msg; //todo maybe return header instead

    // ===================== SDP Header =====================
    msg.flags       = 0x07; // No reply required TODO for now.. hmm how do I do replies?
    msg.tag         = 0;    // 0 = Send internally (not over the Ethernet)

    msg.srce_addr   = spin1_get_chip_id();
    msg.srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    msg.dest_addr   = spin1_get_chip_id(); // Destination core is on the same chip
    msg.dest_port   = (SDP_PORT << PORT_SHIFT) | dest_core;

    return msg;
}