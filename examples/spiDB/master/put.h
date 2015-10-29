#include "../sdram_writer.h"

#include <debug.h>

bool put(core_dsg dsg, uint32_t info, void* k, void* v){
    //TODO if fails, we need to rollback

    //try(address);
    if(!dsg.data_current || !*dsg.data_current){
        return false;
    }

    try(append(dsg.data_current, &info, 1)); //sizeof(uint32_t))
    //try(store_to_sdram(&v_type_and_size, 1)); //sizeof(uint32_t))

    uint16_t k_size = (info & 0x0FFF0000) >> 16; //TODO make sure this is right...
    uint16_t v_size = info & 0x00000FFF;

    uint16_t k_size_words = (k_size+3)/4;
    uint16_t v_size_words = (v_size+3)/4;

    try(append(dsg.data_current, k, k_size_words));//TODO hmmm NO
    try(append(dsg.data_current, v, v_size_words));

    //update core's space in system to tell where it should end the reading
    **dsg.data_start += 1 + k_size_words + v_size_words;

    //try(write(dsg.data_start, v, words_written); //*4)
    return true;
}