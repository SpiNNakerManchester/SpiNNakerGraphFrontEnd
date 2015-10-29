
#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

#include <debug.h>

typedef enum { NUL, UINT32, STRING } var_type;

typedef enum regions_e {
    SYSTEM_REGION, DB_DATA_REGION
} regions_e;

#define try(cond) do { if (!cond) return false; } while (0)

typedef struct core_dsg {
    address_t* data_start;
    address_t* data_current;
} core_dsg;

typedef enum {
    SEND_DATA_REGION,
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

uint32_t to_info(var_type type, size_t size){
    return  size | ((type) << 12);
}

uint32_t to_info1(var_type type, void* data){
    return to_info(type, get_size_bytes(data,type));
}

uint32_t to_info2(var_type k_type, var_type v_type, void* k, void* v){
   return (to_info1(k_type,k) << 16) | to_info1(v_type,v);
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
  //log_info("  data:      %08x", *msg.data);
  log_info("=============================================");
}

#endif