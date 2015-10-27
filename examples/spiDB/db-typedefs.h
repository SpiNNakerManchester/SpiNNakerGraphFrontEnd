
#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

#include <debug.h>

//---------------------------------------
// Structures
//---------------------------------------
//! structure that defines a channel in memory.
typedef struct recording_channel_t {
    size_t current_size;
    uint8_t *start;
    uint8_t *current;
    uint8_t *end;
} recording_channel_t;

recording_channel_t recording_channel;

#define try(cond) do { if (!cond) return false; } while (0)

typedef enum { NUL, UINT32, STRING } var_type;

typedef enum {
    STATE,
    PUT,
    PULL,
    UPDATE,
    REMOVE
} dbCommand;

typedef struct value_entry {
    var_type type;
    size_t size;
    void* data;
} value_entry;

uint32_t get_size_bytes(void* data, var_type t){
    switch(t){
        case UINT32: return sizeof(uint32_t);
        case STRING: return strlen((char*)data) * sizeof(char);
        case NUL:
        default:     return 0;
    }
}

void print_msg(sdp_msg_t msg){
  log_info("=============================================");
  log_info("================= SDP INFO ==================");
  log_info("  length:    %04x", msg.length);
  log_info("=============================================");
  log_info("================ SDP HEADER =================");
  log_info("  flags:     %02x", msg.flags);
  log_info("  tag:       %02x", msg.tag);
  log_info("  dest_addr: %04x", msg.dest_addr);
  log_info("  dest_port: %02x", msg.dest_port);
  log_info("  srce_addr: %04x", msg.srce_addr);
  log_info("  srce_port: %02x", msg.srce_port);
  log_info("=============================================");
  log_info("============== SDP DATASPACE ================");
  log_info("  cmd_rc:    %04x", msg.cmd_rc);
  log_info("  seq:       %04x", msg.seq);
  log_info("  arg1:      %08x", msg.arg1);
  log_info("  arg2:      %08x", msg.arg2);
  log_info("  arg3:      %08x", msg.arg3);
  log_info("  data[0]:   %02x", msg.data[0]);
  log_info("  data[1]:   %02x", msg.data[1]);
  log_info("  data[2]:   %02x", msg.data[2]);
  log_info("=============================================");
}

#endif