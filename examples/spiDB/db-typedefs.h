
#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

#include <debug.h>

typedef enum { NUL, UINT32, STRING } var_type;

typedef enum regions_e {
    SYSTEM_REGION, DB_DATA_REGION
} regions_e;

typedef struct recorder_t {
    size_t current_size;

    address_t start;
    address_t current;
    address_t end;
} recorder_t;

recorder_t recorder;

#define try(cond) do { if (!cond) return false; } while (0)

typedef enum {
    PUT,
    PULL
} dbCommand;

typedef struct value_entry {
    var_type type;
    size_t size;
    void* data;
} value_entry;

uint16_t get_size_bytes(void* data, var_type t){ //todo what if it's bigger than 16bits?
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
  log_info("  data:      %08x", *msg.data);
  log_info("=============================================");
}

#endif