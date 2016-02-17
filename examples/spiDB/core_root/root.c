/***** root.c/root_summary
*
* COPYRIGHT
*  Copyright (c) The University of Manchester, 2011. All rights reserved.
*  SpiNNaker Project
*  Advanced Processor Technologies Group
*  School of Computer Science
*  Author: Arthur Ceccotti
*******/

#define LOG_LEVEL 40 //debug

#undef PRODUCTION_CODE
#undef NDEBUG

#include "spin1_api.h"
#include <debug.h>
#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "../memory_utils.h"
#include "../sdp_utils.h"
#include <data_specification.h>
#include <simulation.h>
#include <sark.h>
#include <circular_buffer.h>

#define TIMER_PERIOD 100

// Globals
uint32_t time = 0; //represents the microseconds since start
//note: SDP timeouts are in milliseconds

#ifdef DB_TYPE_KEY_VALUE_STORE
    #ifdef DB_SUBTYPE_HASH_TABLE

        uint32_t hash(uchar* bytes, size_t size){
            uint32_t h = 5381;
            for(uint16_t i = 0; i < size; i++){
                h = ((h << 5) + h) + (bytes[i] ^ (bytes[i] << 28));
            }
            return h;
        }
    #endif
#endif

static circular_buffer sdp_buffer;
static circular_buffer capacitor_buffer;

uchar chipx, chipy, core;

Table* tables = NULL;
uint n_tables = 0;

address_t currentQueryAddr;

//100 microseconds
void update (uint ticks, uint b){
    use(ticks);
    use(b);

    time += TIMER_PERIOD;

    //every x ms
    if(ticks % 2 == 0){
        uint i = 0;
        #define CUTOFF 1

        uint32_t mailbox;
        while(++i <= CUTOFF &&
              circular_buffer_get_next(capacitor_buffer, &mailbox)){

            sdp_msg_t* msg = (sdp_msg_t*)mailbox;

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            if(header->cmd != INSERT_INTO){
                log_error("Capacitor buffer contains entry with cmd = %d",
                          header->cmd);
                continue;
            }

            insertEntryQuery* insertE = (insertEntryQuery*) header;
            Entry e = insertE->e;

            uint32_t dest_core = (e.row_id % 11) + FIRST_LEAF;
            log_info("INSERT_INTO '%s' - core %d  < (%s,%s)",
                     insertE->table_name, dest_core, e.col_name, e.value);

            //printEntry(&e);

            set_dest_chip(msg,spin1_get_chip_id());//same chip
            set_dest_core(msg,dest_core);

            while(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                spin1_delay_us(2);
                log_info("Attempting to send INSERT_INTO to %d again",
                         dest_core);
            }
        }
    }
}

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        if(!spin1_trigger_user_event(0, 0)){
            log_error("Unable to trigger user event.");
        }
    }
    else{
        log_error("Unable to add SDP packet to circular buffer.");
    }
}

void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    uint32_t mailbox;
    while(circular_buffer_get_next(sdp_buffer, &mailbox)){

        sdp_msg_t* msg = (sdp_msg_t*)mailbox;

        if(msg->srce_port == PORT_ETH){ //coming from host
            //spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);
            //printQuery(query);

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            if(header->cmd == PING){
                revert_src_dest(msg);
                spin1_send_sdp_msg(msg, SDP_TIMEOUT);
                spin1_msg_free(msg);
                return;
            }

            #ifdef DB_TYPE_KEY_VALUE_STORE

                #ifdef DB_SUBTYPE_HASH_TABLE
                    uint32_t h;
                #endif

                uchar h_chipx, h_chipy, h_core;

            switch(header->cmd){
                case PUT:;
                    log_info("PUT");
                    putQuery* putQ = (putQuery*) header;
                    log_info("  info: %08x, k_v: %s", putQ->info, putQ->k_v);

                    #ifdef DB_SUBTYPE_HASH_TABLE
                        h = hash(putQ->k_v, k_size_from_info(putQ->info));

                        h_chipx =  (h & 0x00FF0000 >> 16) % CHIP_X_SIZE;
                        h_chipy =  (h & 0x0000FF00 >> 8)  % CHIP_Y_SIZE;
                        h_core  = ((h & 0x000000FF)       % CORE_SIZE)
                                    + FIRST_LEAF;
                    #else
                        h_chipx = 0;
                        h_chipy = 0;
                        h_core = (putQ->id % NUMBER_OF_LEAVES)
                                  + FIRST_LEAF;
                    #endif

                    set_dest_xyp(msg, h_chipx, h_chipy, h_core);

                    if(spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                        log_info("  Sent to (%d,%d,%d)",
                                 h_chipx, h_chipy, h_core);
                    }
                    else {
                        log_error("Unable to send PUT (%s) to (%d,%d,%d)",
                                  putQ->k_v, h_chipx, h_chipy, h_core);
                    }

                    break;
                case PULL:;
                    log_info("PULL");
                    pullQuery* pullQ = (pullQuery*) header;
                    log_info("  info: %08x, k_v: %s", pullQ->info, pullQ->k);

                    #ifdef DB_SUBTYPE_HASH_TABLE
                        h = hash(putQ->k_v, k_size_from_info(putQ->info));

                        h_chipx =  (h & 0x00FF0000 >> 16) % CHIP_X_SIZE;
                        h_chipy =  (h & 0x0000FF00 >> 8)  % CHIP_Y_SIZE;
                        h_core  = ((h & 0x000000FF)       % CORE_SIZE)
                                    + FIRST_LEAF;

                        set_dest_xyp(msg, h_chipx, h_chipy, h_core);

                        if(spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                            log_info("  Sent to (%d,%d,%d)",
                                     h_chipx, h_chipy, h_core);
                        }
                        else {
                            log_error("Unable to send PULL (%s) to (%d,%d,%d)",
                                      pullQ->k, h_chipx, h_chipy, h_core);
                        }
                    #else
                        address_t a = append(&currentQueryAddr,
                                             pullQ, sizeof(pullQuery));

                        if(!a){
                            log_error("Error storing pullQuery to SDRAM.");
                            return;
                        }

                        //broadcast pointer to message over Multicast
                        while(!spin1_send_mc_packet(myKey, a, WITH_PAYLOAD)){
                            log_info("Attempting to send PULL MC packet again.");
                            spin1_delay_us(1);
                        }
                    #endif
                    break;
                default:;
                    break;
            }
            #endif
            #ifdef DB_TYPE_RELATIONAL

            switch(header->cmd){
                case CREATE_TABLE:;
                    log_info("CREATE");
                    createTableQuery* q = (createTableQuery*) header;
                    Table* t = &q->table;

                    Table* newTable;

                    if(getTable(tables, t->name)){
                        log_error("Table with name '%s' already exists.");
                        newTable = NULL;
                    }
                    else{
                        uint32_t row_size = 0;
                        for(uint32_t i = 0; i < t->n_cols; i++){
                            //round up to the closest power of 4
                            //as Spinnaker is word aligned
                            t->cols[i].size = ((t->cols[i].size + 3) / 4) * 4;
                            row_size += t->cols[i].size;
                        }
                        t->row_size = row_size;

                        newTable = (Table*)(data_region + n_tables * sizeof(Table));
                        write(newTable, t, sizeof(Table));

                        log_info("  Table '%s'-> %08x", newTable->name, newTable);
                        print_table(newTable);
                    }

                    revert_src_dest(msg);

                    msg->length = sizeof(sdp_hdr_t) + 9;

                    Response* response = (Response*)&msg->cmd_rc;
                    response->id  = q->id;
                    response->cmd = CREATE_TABLE;
                    response->success = newTable ? true : false;
                    response->x = chipx;
                    response->y = chipy;
                    response->p = core;

                    n_tables++;

                    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                        log_error("Unable to send CREATE_TABLE ack");
                    }

                    break;
                case INSERT_INTO:;
                    log_info("INSERT_INTO");
                    sdp_msg_t* msg_cpy = (sdp_msg_t*) sark_alloc(1,
                                sizeof(sdp_hdr_t) + sizeof(insertEntryQuery));

                    //copy message out of the buffer, so it will not be
                    //written to when a new message arrives
                    sark_word_cpy(msg_cpy, msg,
                        sizeof(sdp_hdr_t) + sizeof(insertEntryQuery));

                    if (!circular_buffer_add(capacitor_buffer, msg_cpy)) {
                        log_error("  Unable to add to capacitor_buffer.");
                        return;
                    }
                    break;
                case SELECT:;
                    print_SELECT((selectQuery*)header);
                    //log_info("SELECT from '%s'", ((selectQuery*)header)->table_name);

                    //store SELECT query message to SDRAM
                    //so it can be read by other cores

                    address_t a = append(&currentQueryAddr,
                                         (selectQuery*)header,
                                         sizeof(selectQuery));

                    if(!a){
                        log_error("Error storing selectQuery to SDRAM.");
                        return;
                    }

                    //broadcast pointer to message over Multicast
                    while(!spin1_send_mc_packet(myKey, a, WITH_PAYLOAD)){
                        log_info("Attempting to send MC packet again.");
                        spin1_delay_us(1);
                    }

                    log_info("Sent SELECT MC packet.");
                    break;
                default:;
                    log_info("[Warning] cmd not recognized: %d with id %d",
                             header->cmd, header->id);
                    break;
            }
            #endif
        }
        else{
            log_info("Unwanted message.....");
        }

        // free the message to stop overload
        spin1_msg_free(msg);
    }
}

void c_main(){
    chipx = spin1_get_chip_id() & 0xF0 >> 8;
    chipy = spin1_get_chip_id() & 0x0F;
    core  = spin1_get_core_id();

    log_info("Initializing Root...");

    if (!initialize_with_MC_key()) {
        rt_error(RTE_SWERR);
    }

    tables = (Table*) data_region;

    //tables = (Table**)sark_alloc(DEFAULT_NUMBER_OF_TABLES, sizeof(Table*));

    currentQueryAddr = data_region + sizeof(Table) * DEFAULT_NUMBER_OF_TABLES ;

    //timer tick in microseconds
    spin1_set_timer_tick(TIMER_PERIOD);

    //Global assignments
    //unreplied_puts  = init_double_linked_list();
    //unreplied_pulls = init_double_linked_list();

    sdp_buffer       = circular_buffer_initialize(200);
    capacitor_buffer = circular_buffer_initialize(200);

    /*
    TODO keep track of how full each core is
    core_db_current_sizes = (size_t***)
                            sark_alloc(CHIP_X_SIZE, sizeof(size_t**));

    for(int x = 0; x < CHIP_X_SIZE; x++){
        core_db_current_sizes[x] = (size_t**)
                                   sark_alloc(CHIP_Y_SIZE, sizeof(size_t*));

        for(int y = 0; y < CHIP_Y_SIZE; y++){
            core_db_current_sizes[x][y] = (size_t*)
                                          sark_alloc(CORE_SIZE, sizeof(size_t));

            for(int c = 0; c < CORE_SIZE; c++){
                 core_db_current_sizes[x][y][c] = 0;
            }
        }
    }
    */

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, 0);
    spin1_callback_on(TIMER_TICK,       update,              1);
    spin1_callback_on(USER_EVENT,       process_requests,    2);

    // kick-start the update process
    //spin1_schedule_callback(send_first_value, 0, 0, 3);

    simulation_run();
}