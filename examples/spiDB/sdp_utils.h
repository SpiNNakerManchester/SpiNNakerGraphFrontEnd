#include "spin1_api.h"
#include <debug.h>

#define SDP_PORT        3
#define SDP_TIMEOUT     10
#define MAX_RETRIES     3

void revert_src_dest(sdp_msg_t* msg){
    uint16_t dest_port = msg->dest_port;
    uint16_t dest_addr = msg->dest_addr;

    msg->dest_port = msg->srce_port;
    msg->dest_addr = msg->srce_addr;

    msg->srce_port = dest_port;
    msg->srce_addr = dest_addr;
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

sdp_msg_t* create_sdp_header_to_host(){
    sdp_msg_t* msg = (sdp_msg_t*) sark_alloc(1, sizeof(sdp_msg_t));

    // ===================== SDP Header =====================
    msg->flags       = 0x07;
    msg->tag         = 0;    // 0 = Send internally (not over the Ethernet)

    msg->srce_addr   = spin1_get_chip_id();
    msg->srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    msg->dest_addr   = 0;
    msg->dest_port   = PORT_ETH;

    return msg;
}

void set_dest_chip(sdp_msg_t* msg, uint32_t dest_chip){
    msg->dest_addr   = dest_chip;
}

void set_dest_core(sdp_msg_t* msg, uint8_t dest_core){
    msg->dest_port   = (SDP_PORT << PORT_SHIFT) | dest_core;
}

void set_dest_xyp(sdp_msg_t* msg, uint8_t x, uint8_t y, uint8_t p){
    set_dest_chip(msg, (x << 8) | y);
    set_dest_core(msg, p);
}

uint32_t get_srce_chip_x(sdp_msg_t* msg){
    return msg->srce_addr & 0xF0 >> 8;
}

uint32_t get_srce_chip_y(sdp_msg_t* msg){
    return msg->srce_addr & 0x0F;
}

uint32_t get_srce_core(sdp_msg_t* msg){
    return msg->srce_port & 0x1F;
}

uint32_t get_dest_chip_x(sdp_msg_t* msg){
    return msg->dest_addr & 0xF0 >> 8;
}

uint32_t get_dest_chip_y(sdp_msg_t* msg){
    return msg->dest_addr & 0x0F;
}

uint32_t get_dest_core(sdp_msg_t* msg){
    return msg->dest_port & 0x1F;
}

void print_msg_header(sdp_msg_t* msg){
  log_info("=============================================");
  log_info("================= SDP INFO ==================");
  log_info("  length:    %04x", msg->length);
  log_info("=============================================");
  log_info("================ SDP HEADER =================");
  log_info("  flags:     %02x", msg->flags);
  log_info("  tag:       %02x", msg->tag);
  log_info("  dest_addr: %04x - chip (%d,%d)",
           msg->dest_addr, get_dest_chip_x(msg), get_dest_chip_y(msg));
  log_info("  dest_port: %02x   - core (%d)",
           msg->dest_port, get_dest_core(msg));
  log_info("  srce_addr: %04x - chip (%d,%d)",
           msg->srce_addr, get_srce_chip_x(msg), get_srce_chip_y(msg));
  log_info("  srce_port: %02x   - core (%d)",
           msg->srce_port, get_srce_core(msg));
}

void print_msg(sdp_msg_t* msg){
  print_msg_header(msg);
  log_info("=============================================");
  log_info("============== SDP DATASPACE ================");
  log_info("  cmd_rc:    %04x", msg->cmd_rc);
  log_info("  seq:       %04x", msg->seq);
  log_info("  arg1:      %08x", msg->arg1);
  log_info("  arg2:      %08x", msg->arg2);
  log_info("  arg3:      %08x", msg->arg3);
  log_info("  data:      %08x (str:%s) (int:%d)",
           msg->data, msg->data, *((uint32_t*)msg->data));
  log_info("=============================================");
}