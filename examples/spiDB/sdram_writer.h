#ifndef __SDRAM_WRITER_H__
#define __SDRAM_WRITER_H__

//todo reader as well to be honest!

#include <data_specification.h>
#include <string.h>
#include "db-typedefs.h"

typedef struct reader_t {
    address_t start_addr;
    address_t size_words_addr;
} reader_t;

reader_t reader;

void reader_init(address_t region){
    reader.size_words_addr = (address_t) &region[0];
    reader.start_addr      = (address_t) &region[1];
}

/*bool writer_init(address_t region, uint32_t size_bytes){

    writer.start     = (address_t) &region[0];
    writer.current   = (address_t) &region[0];
    writer.end       = writer.start + size_bytes;

    writer.current_size = 0;

    return true;
}*/

/*
void clear(){
    for(address_t addr = writer.start; addr <= writer.current; addr++){
        *addr = 0;
    }
}
*/

// returns address of where data was written. NULL if not written
bool append(address_t* address, void* data, uint32_t size_words){ //TODO should it be bytes??

    if(!data || size_words <= 0){ return false; }

    // If there's space to record
    //if (writer.current + size_words <= writer.end) {

        // Copy data into recording channel
        memcpy(*address, data, size_words << 2); // <<2 because it takes bytes

        *address += size_words;

        //address_t addr = writer.current;

        // Update current pointer
        //writer.current += size_words;

        //writer.current_size += size_words;

        return true;
    //} else {
    //    return false;
    //}
}

bool write(address_t address, void* data, uint32_t size_words){ //TODO should it be bytes??
    if(!data || size_words <= 0){ return false; }

    memcpy(address, data, size_words << 2);

    return true;
}


/*address_t write(address_t address, void* data, uint32_t size_words){ //TODO should it be bytes??

    if(!data || size_words <= 0){ return false; }

    // If there's space to record
    if (writer.current + size_words <= writer.end) {

        // Copy data into recording channel
        memcpy(writer.current, data, size_words << 2); // <<2 because it takes bytes

        address_t addr = writer.current;

        // Update current pointer
        writer.current += size_words;

        writer.current_size += size_words;

        return addr;
    } else {
        return NULL;
    }
}*/

address_t system_region;
address_t data_region;

static bool initialize() {

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpec data address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read Dataspec header");
        return false;
    }

    system_region = data_specification_get_region(SYSTEM_REGION, address);
    data_region   = data_specification_get_region(DB_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    uint32_t data_region_size = 500;

    //, data_region_size todo how about the size?
    reader_init(data_region);

    //todo clear data at the start?

    log_info("Initialization completed successfully!");
    return true;
}

#endif