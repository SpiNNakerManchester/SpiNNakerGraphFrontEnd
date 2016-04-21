#ifndef __MEMORY_UTILS_H__
#define __MEMORY_UTILS_H__

#include <data_specification.h>
#include <string.h>
#include "db-typedefs.h"
#include <debug.h>

// returns address of where data was written
address_t append(address_t* address, void* data, size_t size_bytes){
    try(address && data && size_bytes);

    address_t old_addr = *address;

    sark_mem_cpy(*address, data, size_bytes);
    *address += (size_bytes+3) >> 2;

    return old_addr;
}

bool write(address_t address, void* data, size_t size_bytes){
    try(address && data && size_bytes);

    sark_word_cpy(address, data, size_bytes);

    return true;
}

void clear(address_t address, size_t words){
    for(size_t i = 0; i < words; i++){
        address[i] = 0;
    }
}

bool arr_equals(uchar* a, uchar* b, uint32_t n){
    try(n > 0);

    for(uint32_t i = 0; i < n; i++){
        if(a[i] == 0){
            return true;
        }
        if(a[i] != b[i]){
            return false;
        }
    }
    return true;
}

#endif