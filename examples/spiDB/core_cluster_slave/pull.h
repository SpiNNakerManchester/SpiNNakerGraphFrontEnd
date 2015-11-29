#include "../db-typedefs.h"
#include "../sdram_writer.h"

value_entry* pull(address_t addr, uint32_t k_info, uchar* k){

    var_type k_type = (k_info & 0x0000F000) >> 12;
    uint16_t k_size =  k_info & 0x00000FFF;

/*  address_t current_addr      = reader.start_addr;
    size_t    total_size_words  = *reader.size_words_addr;
    address_t end_addr          = current_addr + total_size_words;*/

    uint32_t info = 0;

    //Get 32 bit information for the database entry
    // [4 bits key type, 12 bits key size, 4 bits value type, 12 bits value size]
    while((info = *addr) != 0){

        addr++;

        var_type read_k_type = (info & 0xF0000000) >> 28;
        uint16_t read_k_size = (info & 0x0FFF0000) >> 16;

        var_type v_type      = (info & 0x0000F000) >> 12;
        uint16_t v_size      =  info & 0x00000FFF;

        uint16_t k_size_words = (read_k_size+3) >> 2;
        uint16_t v_size_words = (v_size+3) >> 2;

        if(read_k_type != k_type || read_k_size != k_size){
            addr += k_size_words + v_size_words;
            continue;
        }

        uchar* k_found = (uchar*)addr;
        addr += k_size_words;

        uchar* v_found = (uchar*)addr;
        addr += v_size_words;

        if(arr_equals(k,k_found,k_size)){
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