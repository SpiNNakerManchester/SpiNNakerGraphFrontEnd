#include "../sdram_writer.h"
#include "../db-typedefs.h"
#include <debug.h>

bool put(address_t* addr, uint32_t info, void* k, void* v){

    size_t k_size = k_size_from_info2(info);
    size_t v_size = v_size_from_info2(info);

    append(addr, &info, sizeof(uint32_t));
    append(addr, k,     k_size);
    append(addr, v,     v_size);

    return true;
}