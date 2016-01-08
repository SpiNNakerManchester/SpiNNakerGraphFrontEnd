#ifndef __MEMORY_UTILS_H__
#define __MEMORY_UTILS_H__

#include <data_specification.h>
#include <string.h>
#include "db-typedefs.h"
#include <debug.h>

//todo take it out of here!!
void printEntry(Entry* e){
    log_info("####### Entry #######");
    log_info("row_id: %d", e->row_id);
    log_info("col_name: %s", e->col_name);
    log_info("size: %d", e->size);
    log_info("value: %s", e->value);
}

void print_table(Table* t){
    log_info("####### TABLE #######");
    log_info("t->n_cols %d", t->n_cols);
    log_info("t->row_size %d", t->row_size);
    log_info("t->current_n_rows %d", t->current_n_rows);

    for(uint i = 0; i < t->n_cols; i++){
        log_info("t->cols[%d] = name: %s, type: %d, size: %d",
                    i, t->cols[i].name, t->cols[i].type, t->cols[i].size);
    }
}

// returns address of where data was written. NULL if not written
void append(address_t* address, void* data, uint32_t size_bytes){
    memcpy(*address, data, size_bytes);
    *address += (size_bytes+3) >> 2;
}

bool write(address_t address, void* data, size_t size_bytes){
    if(!data || size_bytes <= 0){ return false; }

    memcpy(address, data, size_bytes);

    return true;
}

void clear(address_t address, size_t words){
    for(size_t i = 0; i < words; i++){
        address[i] = 0;
    }
}

address_t system_region;
address_t data_region;

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

    log_info("Initialization completed successfully!");
    return true;
}

#endif