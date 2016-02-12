#ifndef __PULL_H__
#define __PULL_H__

#include "../db-typedefs.h"
#include "../memory_utils.h"

value_entry* pull(address_t addr, uint32_t info, uchar* k){

    var_type k_type = k_type_from_info(info);
    size_t k_size   = k_size_from_info(info);

    uint32_t curr_info = 0;

    /* Get 32 bit information for the database entry
         4 bits key type,
         12 bits key size,
         4 bits value type, 12 bits value size */
    while((curr_info = *addr) != 0){

        addr++;

        var_type read_k_type = k_type_from_info(curr_info);
        size_t   read_k_size = k_size_from_info(curr_info);

        var_type v_type      = v_type_from_info(curr_info);
        size_t   v_size      = v_size_from_info(curr_info);

        size_t k_size_words = (read_k_size+3) >> 2;
        size_t v_size_words = (v_size+3) >> 2;

        if(read_k_type != k_type || read_k_size != k_size){
            addr += k_size_words + v_size_words;
            continue;
        }

        uchar* k_found = (uchar*)addr;
        addr += k_size_words;

        uchar* v_found = (uchar*)addr;
        addr += v_size_words;

        if(arr_equals(k,k_found,k_size)){
            value_entry* v = (value_entry*)sark_alloc(1, sizeof(value_entry));
            v->data = v_found;
            v->size = v_size;
            v->type = v_type;

            return v;
        }
        else{
            continue;
        }
    }

    return NULL;
}
#endif