#include "../sdram_writer.h"
#include <debug.h>

bool put(core_data_address_t core_data_address, uint32_t info, void* k, void* v){
    //TODO if fails, we need to rollback

    //try(address);
    if(!core_data_address.data_current || !*core_data_address.data_current){
        return false;
    }

    try(append(core_data_address.data_current, &info, sizeof(uint32_t)));

    uint16_t k_size = (info & 0x0FFF0000) >> 16;
    uint16_t v_size = info & 0x00000FFF;

    try(append(core_data_address.data_current, k, k_size));
    try(append(core_data_address.data_current, v, v_size));

    //update core's space in system to tell where it should end the reading
    **core_data_address.data_start += 1 + (k_size+3)/4 + (v_size+3)/4; //size words todo more efficient way?

    return true;
}