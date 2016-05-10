#ifndef _PULL_TESTS_
#define _PULL_TESTS_
/*
#include "../../test.h"
#include "put_tests.c"
#include "../../db-typedefs.h"

extern value_entry* pull(uint32_t k_info, void* k);

void pull_nothing(){
    assert_t(pull(UINT32,&ONE) == NULL, "Pulled value when DB sdram was empty");
}

void pull_not_there(){
    assert_t(pull(UINT32,&THREE) == NULL, "Pulled value which was not present.");
}

bool pull_assert(var_type k_type, uint16_t k_size, var_type expected_v_type, size_t expected_v_size,
                 void* k, void* expected_v){

    uint32_t k_info = k_size | (k_type << 12);
    assert_t(false, "sending k_info %08x", k_info);

    value_entry* v = pull(k_info,k);

    assert_t(v != NULL, "Could not find key %08x (s:%s)", *((uint32_t*)k), k);
    try(v != NULL);

    assert_t(v->type == expected_v_type,
             "Pulled key (*:%d) (s:%s), returning unexpected type %d, instead of expected %d",
             *((uint32_t*)k), (char*)k, v->type, expected_v_type);
    try(v->type == expected_v_type);

    assert_t(v->size == expected_v_size,
             "Pulled key (*:%d) (s:%s), returning  unexpected size %d, instead of expected %d",
             *((uint32_t*)k), (char*)k, v->size, expected_v_size);
    try(v->size == expected_v_size);

    assert_t(v->data != NULL,
            "Pulled key (*:%d) (s:%s), returning  NULL data.",
             *((uint32_t*)k), (char*)k);
    try(v->data != NULL);

    bool eq = false;

    switch(k_type){
        case STRING:;
            eq = strncmp((char*)(v->data), (char*)expected_v, expected_v_size) == 0;
            break;
        case UINT32:;
            eq = *((uint32_t*)(v->data)) == *((uint32_t*)expected_v);
            break;
        default:;
            eq = false;
            break;
    }

    assert_t(eq, "Pulled key (*:%d) (s:%s), returning unexpected data (*:%d) (s:%s). Expected (*:%d) (s:%s)",
                   *((uint32_t*)k),             (char*)k,
                   *((uint32_t*)v->data),       (char*)v->data,
                   *((uint32_t*)expected_v),    (char*)expected_v);
    try(eq);

    return true;

    //todo free v ??
}

void pull_limits(){
    for(int i=-2; i<=2; i++){
        //for(int j=-1; j<=2; j++){
            try_put(UINT32, UINT32, &i,&i);
            pull_assert(UINT32, 4, UINT32, 4, &i,&i);
        //}
    }
}

void pull_strings(){
    put_strings();

    pull_assert(UINT32, 4, STRING, 5, &THREE,   "Hello");
    pull_assert(STRING, 5, UINT32, 4, "Hello", &THREE);

    pull_assert(STRING, 4, STRING, 3, "Test", "ing");

    pull_assert(STRING, 12, STRING, 45, "My short key", "a kind of relatively long string for testing");
}

void run_pull_tests(){
    log_info("Starting pull tests.");
    pull_nothing();

    pull_limits();

    pull_not_there();

    pull_strings();
    log_info("Finished pull tests.");

}
*/

#endif
