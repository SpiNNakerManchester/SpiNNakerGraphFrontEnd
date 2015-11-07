#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

#define MASTER_CORE_ID  1
#define FIRST_SLAVE     2
#define LAST_SLAVE      16

typedef enum { NUL, UINT32, STRING } var_type;

typedef enum regions_e {
    SYSTEM_REGION, DB_DATA_REGION
} regions_e;

#define try(cond) do { if (!cond) return false; } while (0)

typedef enum spiDBcommand {
    PUT = 0,
    PULL,
    PUT_REPLY,
    PULL_REPLY,
    SLAVE_PULL_REPLY,
    MASTER_PULL_REPLY_ACK,
} spiDBcommand;

typedef struct spiDBquery {
    spiDBcommand cmd;

    var_type k_type;
    size_t   k_size;
    uchar k[128];

    //these are ignored in case of a PULL
    var_type v_type;
    size_t   v_size;
    uchar v[128];
} spiDBquery;

typedef struct value_entry {
    var_type type;
    size_t size;
    void* data;
} value_entry;

uint16_t get_size_bytes(void* data, var_type t){
    switch(t){
        case UINT32: return sizeof(uint32_t);
        case STRING: return strlen((char*)data) * sizeof(char);
        case NUL:
        default:     return 0;
    }
}

uint32_t to_info1(var_type type, size_t size){
    return  size | ((type) << 12);
}

/*
uint32_t to_info1(var_type type, void* data){
    return to_info(type, get_size_bytes(data,type));
}

uint32_t to_info2(var_type k_type, var_type v_type, void* k, void* v){
    return (to_info1(k_type,k) << 16) | to_info1(v_type,v);
}
*/
uint32_t to_info2(var_type k_type, size_t k_size, var_type v_type, size_t v_size){
    return (to_info1(k_type,k_size) << 16) | to_info1(v_type,v_size);
}

size_t k_size_from_info2(uint32_t info){
    return (info & 0x0FFF0000) >> 16;
}

size_t v_size_from_info2(uint32_t info){
    return info & 0x00000FFF;
}


#endif