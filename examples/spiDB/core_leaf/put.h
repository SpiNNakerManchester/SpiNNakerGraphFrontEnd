#ifdef DB_TYPE_KEY_VALUE_STORE
    #ifndef __PUT_H__
        #define __PUT_H__

        #include "../memory_utils.h"
        #include "../db-typedefs.h"

        bool put(address_t* addr, uint32_t info, void* k, void* v){

            size_t k_size = k_size_from_info(info);
            size_t v_size = v_size_from_info(info);

            try(k_size && v_size && k && v); //return false if any of these are 0

            append(addr, &info, sizeof(uint32_t));
            append(addr, k,     k_size);
            append(addr, v,     v_size);

            return true;
        }
    #endif
#endif