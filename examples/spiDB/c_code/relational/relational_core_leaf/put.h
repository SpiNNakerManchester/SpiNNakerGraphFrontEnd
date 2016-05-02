#ifdef DB_TYPE_KEY_VALUE_STORE
    #ifndef __PUT_H__
        #define __PUT_H__

        #include "../../common/memory_utils.h"
        #include "../../common/db-typedefs.h"

        size_t put(address_t* addr, info_t info, void* k, void* v){

            size_t k_size = k_size_from_info(info);
            size_t v_size = v_size_from_info(info);

            try(k_size && v_size && k && v);

            append(addr, &info, sizeof(info_t));
            append(addr, k,     k_size);
            append(addr, v,     v_size);

            return sizeof(info_t) +
                   MULTIPLE_OF_4(k_size) +
                   MULTIPLE_OF_4(v_size);
        }
    #endif
#endif