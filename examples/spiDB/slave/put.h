#include "../db-typedefs.h"
#include <data_specification.h>
#include <string.h>

bool recording_init(address_t region, uint32_t size_bytes){

    //*recorder.counter = 0; //todo what was the counter?

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

bool put(uint32_t k_type_and_size, uint32_t v_type_and_size, void* k, void* v){
    //TODO if fails, we need to rollback

    try(store_to_sdram(&k_type_and_size, 1)); //sizeof(uint32_t))
    try(store_to_sdram(&v_type_and_size, 1)); //sizeof(uint32_t))

    uint32_t k_size = k_type_and_size & 0x0FFFFFFF; //TODO make sure this is right...
    uint32_t v_size = v_type_and_size & 0x0FFFFFFF;

    try(store_to_sdram(k, ((k_size+3)/4)));// *4)); //TODO hmmm NO
    try(store_to_sdram(v, ((v_size+3)/4))); //*4)

    return true;
}