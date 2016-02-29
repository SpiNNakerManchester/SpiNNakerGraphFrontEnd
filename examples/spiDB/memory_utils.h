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
        if(a[i] != b[i]){
            return false;
        }
    }
    return true;
}

address_t system_region, data_region;
uint32_t myKey;

static bool initialize() {
    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpecification address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read DataSpecification header");
        return false;
    }

    system_region = data_specification_get_region(SYSTEM_REGION, address);
    check_sdram(system_region);

    data_region   = data_specification_get_region(DB_DATA_REGION, address);
    check_sdram(data_region);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    clear(data_region, CORE_DATABASE_SIZE_WORDS);

    log_info("Initialization completed successfully!");
    return true;
}

static bool initialize_with_MC_key() {
    bool init = initialize();

    //myKey = system_region[4];

    if(chipx == 0 && chipy == 0){
        myKey = 0;
    }
    else if(chipx == 0 && chipy == 1){
        myKey = 1;
    }
    else if(chipx == 1 && chipy == 0){
        myKey = 2;
    }
    else if(chipx == 1 && chipy == 1){
        myKey = 3;
    }

    log_info("My key is %d", myKey);

    return init;
}

#endif