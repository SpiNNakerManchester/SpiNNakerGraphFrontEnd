#ifndef _PUT_TESTS_
#define _PUT_TESTS_

#include <debug.h>
#include <sark.h>
#include "../../db-typedefs.h"

//TODO should be warning
#define log_assert(message, ...) \
    __log(LOG_INFO, "[ASSERT]   ", message, ##__VA_ARGS__)

#define assert_t(test,msg,...) do { if (!test) log_assert(msg, ##__VA_ARGS__);} while (0)
#define assert_f(test,msg,...) do { if  (test) log_assert(msg, ##__VA_ARGS__);} while (0)
#define run_test(test) do { char* msg = test(); tests_run++; if (msg) return msg; } while (0)

extern bool put(uint32_t k_type_and_size, uint32_t v_type_and_size, void* k, void* v);

uint32_t type_and_size(uint32_t type, void* data){
    return get_size_bytes(data,type) | (type << 28);
}

#define try_put(k_type,v_type,k_data,v_data) \
        do {                                            \
            assert_t(put(type_and_size(k_type,k_data), type_and_size(v_type,v_data), k_data, v_data), \
                     "Failed putting 0x%08x (s: %s) (type: %d) -> 0x%08x (s: %s) (type: %d)",\
                     *k_data, k_data, k_type, *v_data, v_data, v_type); \
        }while(0)

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

    //TODO put the same key twice
    //clean every time??
    put_limits();
    put_random_ints();
    put_strings();

    //test_overflow();

    log_info("Finished running tests.");
 }

#endif