#include "../db-typedefs.h"
#include "../sdram_writer.h"
#include <data_specification.h>
#include <string.h>

#include <debug.h>

value_entry* pull(uint32_t k_info, void* k){

    var_type k_type = (k_info & 0x0000F000) >> 12;
    uint16_t k_size =  k_info & 0x00000FFF;

    address_t current_addr      = reader.start_addr;

    size_t    total_size_words  = *reader.size_words_addr;

    address_t end_addr          = current_addr + total_size_words;

    uint32_t current_word = 1;

    while(current_addr < end_addr){

        uint32_t info = *current_addr;

        current_addr++;

        var_type read_k_type = (info & 0xF0000000) >> 28;
        uint16_t read_k_size = (info & 0x0FFF0000) >> 16;

        var_type v_type      = (info & 0x0000F000) >> 12;
        uint16_t v_size      =  info & 0x00000FFF;

        uint16_t k_size_words = (read_k_size+3) >> 2; //TODO this is stupid...
        uint16_t v_size_words = (v_size+3) >> 2; //todo same here

        if(read_k_type != k_type || read_k_size != k_size){
            current_addr += k_size_words + v_size_words;
            continue;
        }

        void* k_found = (void*)current_addr;
        current_addr += k_size_words;

        void* v_found = (void*)current_addr;
        current_addr += v_size_words;

        bool k_eq = false;

        switch(k_type){
            case STRING:;
                k_eq = strncmp((char*)k, (char*)k_found, k_size) == 0;
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