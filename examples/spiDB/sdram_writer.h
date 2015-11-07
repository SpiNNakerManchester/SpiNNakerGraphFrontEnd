#ifndef __SDRAM_WRITER_H__
#define __SDRAM_WRITER_H__

//todo reader as well to be honest!

#include <data_specification.h>
#include <string.h>
#include "db-typedefs.h"
#include <debug.h>

typedef struct core_data_address_t {
    address_t* data_start;
    address_t* data_current;
} core_data_address_t;

core_data_address_t get_core_data_address(uint32_t core_id) {

    // Get pointer to 1st virtual processor info struct in SRAM
    vcpu_t *sark_virtual_processor_info = (vcpu_t*) SV_VCPU;

    // Get the address this core's DTCM data starts at from the user data member
    // of the structure associated with this virtual processor
    address_t address = (address_t) sark_virtual_processor_info[core_id].user0;

    core_data_address_t core_data_address;
    core_data_address.data_start      = (address_t*) sark_alloc(1, sizeof(address_t));
    core_data_address.data_current    = (address_t*) sark_alloc(1, sizeof(address_t));

    address_t data_address = data_specification_get_region(DB_DATA_REGION, address);

    *core_data_address.data_start     = data_address; //used to store size
    *core_data_address.data_current   = data_address+1;//start from next word

    return core_data_address;
}

void print_core_data_addresses(core_data_address_t* core_data_addresses){
    for(int i=FIRST_SLAVE; i<=LAST_SLAVE; i++){
        log_info("core_dsg[%d].data_start = %08x", i, *core_data_addresses[i].data_start);
    }
}


typedef struct reader_t {
    address_t start_addr;
    address_t size_words_addr;
} reader_t;

reader_t reader;


void reader_init(address_t region){
    reader.size_words_addr = (address_t) &region[0];
    reader.start_addr      = (address_t) &region[1];
}

// returns address of where data was written. NULL if not written
address_t append(address_t* address, void* data, uint32_t size_bytes){

    if(!data || size_bytes <= 0){ return NULL; }

    // If there's space to record
    //if (writer.current + size_words <= writer.end) {

        address_t address_stored = *address;

        // Copy data into recording channel
        memcpy(*address, data, size_bytes); // <<2 because it takes bytes

        *address += (size_bytes+3)/4; //todo fuck no. size words

        return address_stored;
    //} else {
    //    return false;
    //}
}

bool write(address_t address, void* data, uint32_t size_words){ //TODO should it be bytes??
    if(!data || size_words <= 0){ return false; }

    memcpy(address, data, size_words << 2);

    return true;
}

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

    reader_init(data_region); //todo size should not be hardcoded

    log_info("Initialization completed successfully!");
    return true;
}

#endif