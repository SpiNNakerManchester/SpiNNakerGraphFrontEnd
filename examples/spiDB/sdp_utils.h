#include "spin1_api.h"
#include <debug.h>
#include "timer2.h"
#include "db-typedefs.h"

#define SDP_PORT        3
#define SDP_TIMEOUT     10 //milliseconds
#define MAX_RETRIES     3

void revert_src_dest(sdp_msg_t* msg){
    uint16_t dest_port = msg->dest_port;
    uint16_t dest_addr = msg->dest_addr;

    msg->dest_port = msg->srce_port;
    msg->dest_addr = msg->srce_addr;

    msg->srce_port = dest_port;
    msg->srce_addr = dest_addr;
}


void set_dest_host(sdp_msg_t* msg){
    msg->dest_addr   = 0;
    msg->dest_port   = PORT_ETH;
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

void set_srce_as_self(sdp_msg_t* msg){
    msg->srce_addr = spin1_get_chip_id();
    msg->srce_port = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();
}

uchar get_srce_chip_x(sdp_msg_t* msg){
    return (msg->srce_addr & 0xFF00) >> 8;
}

uchar get_srce_chip_y(sdp_msg_t* msg){
    return msg->srce_addr & 0x00FF;
}

uchar get_srce_core(sdp_msg_t* msg){
    return msg->srce_port & 0x1F;
}

uchar get_dest_chip_x(sdp_msg_t* msg){
    return (msg->dest_addr & 0xFF00) >> 8;
}

uchar get_dest_chip_y(sdp_msg_t* msg){
    return msg->dest_addr & 0x00FF;
}

uchar get_dest_core(sdp_msg_t* msg){
    return msg->dest_port & 0x1F;
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

sdp_msg_t* create_sdp_header_to_host_alloc_extra(size_t bytes){
    sdp_msg_t* msg = (sdp_msg_t*) sark_alloc(1, sizeof(sdp_msg_t) + bytes);

    // ===================== SDP Header =====================
    msg->flags       = 0x07;
    msg->tag         = 0;    // 0 = Send internally (not over the Ethernet)

    msg->srce_addr   = spin1_get_chip_id();
    msg->srce_port   = (SDP_PORT << PORT_SHIFT) | spin1_get_core_id();

    msg->dest_addr   = 0;
    msg->dest_port   = PORT_ETH;

    return msg;
}

sdp_msg_t* create_sdp_header_to_host(){
    return create_sdp_header_to_host_alloc_extra(0);
}

sdp_msg_t* send_internal_data_response(uchar x, uchar y, uchar p,
                                       void* data,
                                       size_t data_size_bytes){

    sdp_msg_t* msg = create_sdp_header(0,0);
    set_dest_xyp(msg, x, y, p);
    sark_mem_cpy(&msg->cmd_rc, data, data_size_bytes);

    msg->length = sizeof(sdp_hdr_t) + data_size_bytes;

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send data response (%d, %d, %d)", x, y, p);
        return NULL;
    }

    return msg;
}

#define UNDEF 255

sdp_msg_t* send_xyp_data_response_to_host(spiDBQueryHeader* q,
                                          void* data,
                                          size_t data_size_bytes,
                                          uchar x_origin,
                                          uchar y_origin,
                                          uchar p_origin){

    sdp_msg_t* msg = create_sdp_header_to_host_alloc_extra(
                        data_size_bytes + sizeof(Response_hdr));

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = q->id;
    r->cmd = q->cmd;
    r->success = true;
    r->x = x_origin == UNDEF ? chipx : x_origin;
    r->y = y_origin == UNDEF ? chipy : y_origin;
    r->p = p_origin == UNDEF ? core  : p_origin;

    sark_mem_cpy(&r->data, data, data_size_bytes);

    msg->length = sizeof(sdp_hdr_t) + sizeof(Response_hdr) + data_size_bytes;

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send data response to host");
        return NULL;
    }

    return msg;
}


sdp_msg_t* send_data_response_to_host(spiDBQueryHeader* q,
                                      void* data,
                                      size_t data_size_bytes){
    return send_xyp_data_response_to_host(q, data, data_size_bytes,
                                          UNDEF, UNDEF, UNDEF);
}

sdp_msg_t* send_empty_response_to_host(spiDBQueryHeader* q){
    return send_data_response_to_host(q, NULL, 0);
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