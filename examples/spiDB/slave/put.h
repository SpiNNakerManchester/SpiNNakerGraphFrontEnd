#include "../db-typedefs.h"
#include <data_specification.h>
#include <string.h>

#include <debug.h>

bool recording_init(address_t region, uint32_t size_bytes){

    recorder.start     = (address_t) &region[0];
    recorder.current   = (address_t) &region[0];
    recorder.end       = recorder.start + size_bytes;

    recorder.current_size = 0;

    return true;
}

void clear_data(){
    for(address_t addr = recorder.start; addr <= recorder.current; addr++){
        *addr = 0;
    }
}

bool store_to_sdram(void* data, uint32_t size_bytes){ //TODO NOT REALLY BYTES ANYMORE!

    if(!data || size_bytes <= 0){ return false; }

    // If there's space to record
    if (recorder.current + size_bytes <= recorder.end) {

        // Copy data into recording channel
        memcpy(recorder.current, data, size_bytes*4);

        // Update current pointer
        recorder.current += size_bytes;

        recorder.current_size += size_bytes;

        return true;
    } else {
        return false;
    }
}

bool put(uint32_t info, void* k, void* v){
    //TODO if fails, we need to rollback

    try(store_to_sdram(&info, 1)); //sizeof(uint32_t))
    //try(store_to_sdram(&v_type_and_size, 1)); //sizeof(uint32_t))

    uint16_t k_size = (info & 0x0FFF0000) >> 16; //TODO make sure this is right...
    uint16_t v_size = info & 0x00000FFF;

    try(store_to_sdram(k, ((k_size+3)/4)));// *4)); //TODO hmmm NO
    try(store_to_sdram(v, ((v_size+3)/4))); //*4)

    return true;
}