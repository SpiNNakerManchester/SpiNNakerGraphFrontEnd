/****a* hello_world.c/hello_world_summary
*
* COPYRIGHT
*  Copyright (c) The University of Manchester, 2011. All rights reserved.
*  SpiNNaker Project
*  Advanced Processor Technologies Group
*  School of Computer Science
*  Author: Arthur Ceccotti
*******/

#include "spin1_api.h"
#include "common-typedefs.h"
#include "recording.h"
#include <data_specification.h>
#include <debug.h>


typedef enum regions_e {
    SYSTEM_REGION, STRING_DATA_REGION
} regions_e;

typedef enum { NUL, UINT32, STRING } var_type;

uint32_t get_size_bytes(void* data, var_type t){
    switch(t){
        case UINT32: return sizeof(uint32_t);
        case STRING: return strlen((char*)data) * sizeof(char);
        case NUL:
        default:     return 0;
    }
}

size_t bytes_written = 0;

void store(void* data, uint32_t size_bytes){
    bool recorded = recording_record(e_recording_channel_spike_history, data, size_bytes);

    if(recorded){
        //TODO how about holes in strings?
        bytes_written += size_bytes;
    }

    return recorded;
}


bool put(void* k, var_type k_type, void* v, var_type v_type){

    uint32_t k_size = get_size_bytes(k,k_type);
    uint32_t v_size = get_size_bytes(v,v_type);

    uint32_t k_size_and_type = k_size | ((k_type) << 28);
    uint32_t v_size_and_type = v_size | ((v_type) << 28);

    store(&k_size_and_type, sizeof(uint32_t));
    store(&v_size_and_type, sizeof(uint32_t));

    store(k, ((k_size+3)/4)*4);
    store(v, ((v_size+3)/4)*4);

    return true;
}

char* word_to_char_array(uint32_t word){
    char char_array[4];

    char_array[3] = (word & 0XFF000000) >> 24;
    char_array[2] = (word & 0X00FF0000) >> 16;
    char_array[1] = (word & 0X0000FF00) >> 8;
    char_array[0] = (word & 0X000000FF);

    log_info("char array len is: %d", strlen(char_array)); //TODO hmmmmm what?

    return char_array;
}

char* words_to_char_array(uint32_t* words, uint32_t n_words){

    size_t int32_size = sizeof(uint32_t);

    char* char_ptr = (char*)spin1_malloc(int32_size * n_words);

    for(int i=0; i<n_words; i++){
        memcpy(char_ptr+i*int32_size, word_to_char_array(words[i]), int32_size);
    }

    return char_ptr;
}

typedef struct value {
    var_type type;
    size_t size;
    void* data;
} value;

value null_value(){
    value v;
    v.data = NULL;
    v.size = 0;
    v.type = NUL;

    return v;
}

void get_info(uint32_t bits, var_type* type, size_t* size){
    uint32_t ii = (bits & 0xF0000000) >> 28;
    *type = (bits & 0xF0000000) >> 28;
    *size = (bits & 0x0FFFFFFF);
}

void* value_words_to_type(uint32_t* data, size_t size_words, var_type type){
    switch(type){
        case STRING:    return words_to_char_array(data, size_words);
        case UINT32:    return &(data[0]);
        default:        return NULL;
    }
}



value pull(void* k, var_type k_type){

    address_t address = data_specification_get_data_address();

    address_t data_address = data_specification_get_region(STRING_DATA_REGION, address);

    uint32_t current_word = 1;

    uint32_t lookup_count = 0;

    while(current_word < bytes_written >> 2){

        lookup_count++;

        var_type read_k_type; size_t k_size;
        get_info(data_address[current_word++], &read_k_type, &k_size);
        uint32_t k_size_words = (k_size+3) >> 2;

        var_type v_type; size_t v_size;
        get_info(data_address[current_word++], &v_type, &v_size);
        uint32_t v_size_words = (v_size+3) >> 2;

        uint32_t key_words[k_size_words];
        for(int i=0; i < k_size_words; i++){
            key_words[i] = data_address[current_word++];
        }

        uint32_t value_words[v_size_words];
        for(int i=0; i < v_size_words; i++){
            value_words[i] = data_address[current_word++];
        }

        //TODO THIS CAN BE CHECKED WAY EARLIER, BUT KEEP TRACK OF CURRENT_WORD
        if(read_k_type != k_type){
            log_info("Lookup %d: Given key type: %d != read key type %d", lookup_count, k_type, read_k_type);
            continue;
        }

        switch(k_type){
            case STRING:;
                        char* key_bytes = words_to_char_array(key_words, k_size_words);

                        if(strlen((char*)k) == k_size && strncmp((char*)k, key_bytes, k_size) == 0){

                            log_info("Lookup %d found %s",  lookup_count, (char*)k);

                            value v;
                            v.data = value_words_to_type(value_words, v_size_words, v_type);
                            v.size = v_size;
                            v.type = v_type;

                            return v;
                        }
                        else{
                            log_info("Lookup %d: %s != %s",  lookup_count, (char*)k, key_bytes);
                            continue;
                        }
            case UINT32:;
                        //if(k_size_words != 1){
                            //complain!!! An int 32 should be 1 word long
                        //}

                        if(*((uint32_t*)k) == key_words[0]){

                            log_info("Lookup %d: found %d!", lookup_count, *((uint32_t*)k));

                            value v;
                            log_info("returning type v_type %d ", v_type);
                            log_info("returning size %d ", v_size);
                            v.data = value_words_to_type(value_words, v_size_words, v_type);
                            log_info("v.data (%s)", v.data);

                            for(int i=0;i<v_size;i++){
                                log_info("v.data[%d] is %c (%08x)", i , ((char*)v.data)[i], ((char*)v.data)[i]);
                            }
                            v.size = v_size;
                            v.type = v_type;

                            return v;
                        }
                        else{
                            log_info("Lookup %d: %d != %d",  lookup_count, *((uint32_t*)k), key_words[0]);
                            continue;
                        }
            default:
                        log_info("Lookup %d: invalid type", lookup_count);
                        continue;
        }
    }

    log_info("No more data to lookup. Not found.");

    return null_value();

}

static bool initialize() {

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpec data address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read DataSpec header");
        return false;
    }

    address_t system_region = data_specification_get_region(SYSTEM_REGION, address);
    address_t data_region   = data_specification_get_region(STRING_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    uint32_t data_region_size = 500;

                                               // TODO should make my own channel
    if (!recording_initialse_channel(data_region, e_recording_channel_spike_history, data_region_size)) {
        log_error("Could not initialize channel.");
        return false;
    }

    log_info("Initialization completed successfully!");
    return true;
}

void update (uint ticks, uint b)
{
    return; //do nothing for now!!!
    // I give it a few ticks between reading and writing, just in case
    // the IO operations take a bit of time
    if(ticks == 100){
                              uint32_t one = 1;
                              uint32_t a = 10;
                              uint32_t b = 16;
                              put(&one, UINT32, &one, UINT32);
                              put("I love", STRING, "Spinnaker", STRING);
                              put(&a, UINT32, "hahaz", STRING);
                              put("ah", STRING, &b, UINT32);
                              put("yo", STRING, "boy", STRING);
                              put("I like cheese, man", STRING, "but do you?", STRING);

                              log_info("We wrote a total of %d bytes", bytes_written);
                            }
    else if(ticks == -1)   {
                               // log_info("Hello -> %s", pull("Hello",STRING));
                                 //uint32_t k = 10;
                                 //var_type k_type = UINT32;
                                 //value v = pull(&k,k_type);
                                 char* k = "yo";
                                 var_type k_type = STRING;
                                 value v = pull(k,k_type);

                                    switch(k_type){
                                        case STRING: log_info("STRING Key %s", k);
                                                     break;
                                        case UINT32: log_info("UINT32 Key %d", k);
                                                     break;
                                    }

                                    switch(v.type){
                                        case STRING: log_info("has value -> %s (type: STRING, size: %d)", v.data, v.size);
                                                     break;
                                        case UINT32: log_info("has value -> %d (type: UINT32, size: %d)", *((uint32_t*)v.data), v.size);
                                                     break;
                                        case NUL:
                                        default:     log_info("was not found!");
                                                     break;
                                    }

                            }
    //else if(ticks == 300)   { recording_finalise();
    //                          spin1_exit(0);}
}

void sdp_packet_callback(uint mailbox, uint port) {
    log_info("RECEIVED A PACKET!!!!!!!!!!!!!");

/*    use(port);
    sdp_msg_t *msg = (sdp_msg_t *) mailbox;
    uint16_t length = msg->length;
    eieio_msg_t eieio_msg_ptr = (eieio_msg_t) &(msg->cmd_rc);

    packet_handler_selector(eieio_msg_ptr, length - 8);

    // free the message to stop overload
    spin1_msg_free(msg);*/
}

void c_main()
{
    log_info("Initializing Distributed Hello World...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to 100ms
    spin1_set_timer_tick(100);

    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 0);
    spin1_callback_on(SDP_PACKET_RX, sdp_packet_callback, 1);

    simulation_run();
}