#include "../db-typedefs.h"
#include <data_specification.h>
#include <string.h>

#include <debug.h>

value_entry* pull(var_type k_type, void* k){

    address_t data_address = recorder.start;

    uint32_t current_word = 0;

    uint32_t lookup_count = 0;

    while(current_word < recorder.current_size){

        lookup_count++;

        var_type read_k_type; size_t k_size;
        get_info(data_address[current_word++], &read_k_type, &k_size);
        uint32_t k_size_words = (k_size+3) >> 2;

        var_type v_type; size_t v_size;
        get_info(data_address[current_word++], &v_type, &v_size);
        uint32_t v_size_words = (v_size+3) >> 2;

        if(read_k_type != k_type){
            current_word += k_size_words + v_size_words;
            continue;
        }

        void* k_found = (void*)(&data_address[current_word]);
        current_word += k_size_words;

        void* v_found = (void*)(&data_address[current_word]);
        current_word += v_size_words;

        bool k_eq = false;

        switch(k_type){
            case STRING:;
                k_eq = (strlen((char*)k) == k_size && strncmp((char*)k, (char*)k_found, k_size) == 0);
                break;
            case UINT32:;
                k_eq = *((uint32_t*)k) == *((uint32_t*)k_found);
                break;
            default:;
                continue;
        }

        if(k_eq){
            value_entry* v = (value_entry*)sark_alloc(1, sizeof(value_entry));
            v->data = v_found;
            v->size = v_size;
            v->type = v_type;

            return v;
        }
        else{
            continue;
        }
    }

    return NULL;
}