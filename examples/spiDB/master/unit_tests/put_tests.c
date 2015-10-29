#ifndef _PUT_TESTS_
#define _PUT_TESTS_

#include <sark.h>
#include "../../db-typedefs.h"
#include "../../test.h"

extern bool put(address_t address, uint32_t info, void* k, void* v);
extern address_t* core_regions;

void try_put(var_type k_type, var_type v_type, void* k_data, void* v_data){

    //todo function
    uint16_t k_type_and_size = get_size_bytes(k_data,k_type) | ((k_type) << 12);
    uint16_t v_type_and_size = get_size_bytes(v_data,v_type) | ((v_type) << 12);
    uint32_t info = (k_type_and_size << 16) | v_type_and_size;

    //todo not only on core 2...
    assert_t(put(core_regions[2], info, k_data, v_data) != NULL,
             "Failed putting 0x%08x (s: %s) (type: %d) -> 0x%08x (s: %s) (type: %d)",
             *((uint32_t*)k_data), (char*)k_data, k_type, *((uint32_t*)v_data), (char*)v_data, v_type);
}

int tests_run = 0;

void put_limits(){
    for(int i = -1; i <= 1; i++){
        for(int j = -1; j <= 1; j++){
            try_put(UINT32, UINT32, &i,&j);
        }
    }
}

void put_random_ints(){
    for(int i=0; i < 5; i++){
        uint32_t r1 = sark_rand();
        uint32_t r2 = sark_rand();
        try_put(UINT32, UINT32, &r1,&r2);
    }
}

const uint32_t MINUS_ONE    = -1;
const uint32_t ZERO         =  0;
const uint32_t ONE          =  1;
const uint32_t TWO          =  2;
const uint32_t THREE        =  3;

void put_strings(){
    try_put(UINT32, STRING,  &THREE,   "Hello");
    try_put(STRING, UINT32,  "Hello", &THREE);

    try_put(STRING, STRING,  "Test", "ing");
    try_put(STRING, STRING,  "My short key", "a kind of relatively long string for testing");

    try_put(STRING, STRING, "", "");
    try_put(STRING, STRING, "Foobar", "");
}

void run_put_tests() {
    log_info("Started running tests.");
    //TODO put the same key twice
    //clean every time??
    put_limits();
    put_random_ints();
    put_strings();

    //test_overflow();

    log_info("Finished running tests.");
 }

#endif