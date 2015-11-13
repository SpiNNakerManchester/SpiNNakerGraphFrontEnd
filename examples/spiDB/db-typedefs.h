#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

#define MASTER_CORE_ID  1
#define FIRST_SLAVE     2
#define LAST_SLAVE      16

typedef enum { UINT32, STRING } var_type;

typedef enum regions_e {
    SYSTEM_REGION, DB_DATA_REGION
} regions_e;

#define try(cond) do { if (!cond) return false; } while (0)

typedef enum spiDBcommand {
    PUT = 0,
    PULL,
    CLEAR,

    PUT_REPLY,
    PULL_REPLY,

    PUT_REPLY_ACK, //still needs implementing...
    PULL_REPLY_ACK
} spiDBcommand;

typedef struct spiDBquery {
    uint32_t     id;
    spiDBcommand cmd;

    var_type k_type;
    size_t   k_size;

    //these are ignored in case of a PULL
    var_type v_type;
    size_t   v_size;

    uchar k_v[256];
} spiDBquery;

/*typedef struct spiDBreply {


} spiDBreply;*/

typedef struct value_entry {
    var_type type;
    size_t size;
    uchar* data;
} value_entry;

uint32_t to_info1(var_type type, size_t size){
    return  ((type) << 12) | size;
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