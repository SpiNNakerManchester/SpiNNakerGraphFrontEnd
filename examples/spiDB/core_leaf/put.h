#ifndef __PUT_H__
#define __PUT_H__

#include "../memory_utils.h"
#include "../db-typedefs.h"

bool put(address_t* addr, uint32_t info, void* k, void* v){

    size_t k_size = k_size_from_info(info);
    size_t v_size = v_size_from_info(info);

    append(addr, &info, sizeof(uint32_t));
    append(addr, k,     k_size);
    append(addr, v,     v_size);

    return true;
}

#endif