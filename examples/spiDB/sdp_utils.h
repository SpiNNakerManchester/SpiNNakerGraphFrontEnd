#include "spin1_api.h"
#include <debug.h>
//#include <eieio_interface.h>

#define SDP_PORT        3
#define SDP_TIMEOUT     10
#define MAX_RETRIES     5

void revert_src_dest(sdp_msg_t* msg){
    uchar dest_port_tmp = msg->dest_port;
    uchar dest_addr_tmp = msg->dest_addr;

    msg->dest_port = msg->srce_port;
    msg->dest_addr = msg->srce_addr;
    msg->srce_port = dest_port_tmp;
    msg->srce_addr = dest_addr_tmp;
}

sdp_msg_t* create_sdp_header(uint32_t dest_chip, uint32_t dest_core){
    sdp_msg_t* msg = (sdp_msg_t*) sark_alloc(1, sizeof(sdp_msg_t));

    // ===================== SDP Header =====================
    msg->flags       = 0x87; // Expect reply
    msg->tag         = 0;    // 0 = Send internally (not over the Ethernet)

    msg->srce_addr   = spin1_get_chip_id();
    msg->srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    msg->dest_addr   = dest_chip;
    msg->dest_port   = (SDP_PORT << PORT_SHIFT) | dest_core;

    return msg;
}

sdp_msg_t* create_internal_sdp_header(uint8_t dest_core){
     // Destination core is on the same chip
    return create_sdp_header(spin1_get_chip_id(), dest_core);
}

sdp_msg_t create_sdp_header_to_host(){
    sdp_msg_t msg;

    // ===================== SDP Header =====================
    msg.flags       = 0x87;
    msg.tag         = 0;    // 0 = Send internally (not over the Ethernet)

    msg.srce_addr   = spin1_get_chip_id();
    msg.srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    msg.dest_addr   = 0;
    msg.dest_port   = PORT_ETH;

    return msg;
}


void print_msg(sdp_msg_t* msg){
  log_info("=============================================");
  log_info("================= SDP INFO ==================");
  log_info("  length:    %04x", msg->length);
  log_info("=============================================");
  log_info("================ SDP HEADER =================");
  log_info("  flags:     %02x", msg->flags);
  log_info("  tag:       %02x", msg->tag);
  log_info("  dest_addr: %04x", msg->dest_addr);
  log_info("  dest_port: %02x", msg->dest_port);
  log_info("  srce_addr: %04x", msg->srce_addr);
  log_info("  srce_port: %02x", msg->srce_port);
  log_info("=============================================");
  log_info("============== SDP DATASPACE ================");
  log_info("  cmd_rc:    %04x", msg->cmd_rc);
  log_info("  seq:       %04x", msg->seq);
  log_info("  arg1:      %08x", msg->arg1);
  log_info("  arg2:      %08x", msg->arg2);
  log_info("  arg3:      %08x", msg->arg3);
  log_info("  data:      %08x (%s)", msg->data, msg->data);
  log_info("=============================================");
}

/*
void print_eieio_header(eieio_header_struct* msg){
  log_info("=============================================");
  log_info("================ EIEIO HEADER =================");
  log_info("  apply_prefix:         %08x", msg->apply_prefix);
  log_info("  prefix:               %08x", msg->prefix);
  log_info("  prefix_type:          %08x", msg->packet_type);
  log_info("  key_right_shift:      %08x", msg->key_right_shift);
  log_info("  payload_as_timestamp: %08x", msg->payload_as_timestamp);
  log_info("  payload_apply_prefix: %08x", msg->payload_apply_prefix);
  log_info("  payload_prefix:       %08x", msg->payload_prefix);
  log_info("  count:                %08x", msg->count);
  log_info("  tag:                  %08x", msg->tag);
}
*/