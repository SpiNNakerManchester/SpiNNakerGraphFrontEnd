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
#define QUEUE_SIZE 128

// Globals

static circular_buffer sdp_buffer;
static circular_buffer capacitor_buffer;

extern uchar chipx, chipy, core;

static bool processing_events = false;

#ifdef DB_TYPE_RELATIONAL
    Table* tables = NULL;
    uint n_tables = 0;
#endif

address_t currentQueryAddr;
address_t startQueryAddr;

#ifdef DB_TYPE_KEY_VALUE_STORE
    #ifdef DB_SUBTYPE_HASH_TABLE

        uint32_t hash(uchar* bytes, size_t size){
            #ifdef HASH_FUNCTION_DFJB
                uint32_t h = 5381;

                uint i = 0;
                for(uint i = 0; i < size; i++)
                    h = ((h << 5) + h) + bytes[i];
                return h;
            #endif
            #ifdef HASH_FUNCTION_XOR
                uint32_t h = 0x55555555;

                for(uint i = 0; i < size; i++){
                    h ^= bytes[i];
                    h = h << 5;
                }
                return h;
            #endif
            #ifdef HASH_FUNCTION_JENKINGS
                uint32_t hash, i;
                for(hash = i = 0; i < size; ++i)
                {
                    hash += bytes[i];
                    hash += (hash << 10);
                    hash ^= (hash >> 6);
                }
                hash += (hash << 3);
                hash ^= (hash >> 11);
                hash += (hash << 15);
                return hash;
            #endif
        }
    #endif
#endif

//100 microseconds
void update (uint ticks, uint b){
    use(ticks);
    use(b);

    #ifdef DB_TYPE_RELATIONAL
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

            //printEntry(&e);

            uint32_t dest_core = (e.row_id % 11) + FIRST_LEAF;

            if(e.type == UINT32){
                log_info("INSERT_INTO '%s' - core %d  < (%s,%d) (integer)",
                         insertE->table_name, dest_core,
                         e.col_name, *e.value);
            }
            else{
                log_info("INSERT_INTO '%s' - core %d  < (%s,%s) (varchar)",
                         insertE->table_name, dest_core,
                         e.col_name, e.value);
            }

            set_dest_chip(msg,spin1_get_chip_id());//same chip
            set_dest_core(msg,dest_core);

            while(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                spin1_delay_us(2);
                log_info("Attempting to send INSERT_INTO to %d again",
                         dest_core);
            }

            sark_free(msg);
        }
    }
    #endif
}

sdp_msg_t** msg_cpies;
uint i = 0;

void sdp_packet_callback(register uint mailbox, uint port) {
    use(port);

    // disable interrupts to avoid concurrent triggering of user events
    //uint cpsr = spin1_fiq_disable();

    //uint cpsr = spin1_int_disable();

    i = (i+1)%QUEUE_SIZE;
    register sdp_msg_t* m = msg_cpies[i];

    //log_info("i is %d > %08x", i, msg_cpies[i]);
    //sdp_msg_t* msg_cpy = (sdp_msg_t*)sark_alloc(1,
    //                      sizeof(sdp_hdr_t) + 64); //256?
    //sark_word_cpy(msg_cpy, msg, sizeof(sdp_hdr_t) + 64);
    sark_word_cpy(m, (sdp_msg_t*)mailbox, sizeof(sdp_hdr_t) + 256);

    spin1_msg_free((sdp_msg_t*)mailbox);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, (uint32_t)m)) {

        // disable interrupts to avoid concurrent triggering of user events
        //uint cpsr = spin1_irq_disable();

        if (!processing_events) {
            processing_events = true;
            if(!spin1_trigger_user_event(0, 0)){
                log_error("Unable to trigger user event.");
            }
        }

        // enable interrupts again
        //spin1_mode_restore (cpsr);
    }
    else{
        log_error("Unable to add SDP packet to circular buffer.");
    }

    //spin1_mode_restore (cpsr);
}

//round robin
uchar h_chipx = 0;
uchar h_chipy = 0;
uchar h_core = FIRST_LEAF-1; //-1 because of ++hcore later

void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    //uint i = 0;
    uint32_t mailbox;
    do {
       if (circular_buffer_get_next(sdp_buffer, &mailbox)) {
         /*
         if(++i > 1){
            log_info("number ** %d ** on the queue", i);
         }
         */

        sdp_msg_t* msg = (sdp_msg_t*)mailbox;

        //if(msg->srce_port == PORT_ETH){ //coming from host
        //spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);
        //printQuery(query);

        spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

        if(!header){
            log_info("NULL spiDBQueryHeader received");
            //spin1_msg_free(msg);
            //sark_free(msg);
            continue;
        }

        /*
        if(header->cmd == PING){
            revert_src_dest(msg);
            spin1_send_sdp_msg(msg, SDP_TIMEOUT);
            spin1_msg_free(msg);
            return;
        }
        */
        /*
        if(header->cmd == CLEAR){
            n_tables = 0;
            clear(tables, sizeof(Table) * DEFAULT_NUMBER_OF_TABLES);
            revert_src_dest(msg);
            spin1_send_sdp_msg(msg, SDP_TIMEOUT);

            address_t a = append(&currentQueryAddr,
                                 header, sizeof(spiDBQueryHeader));
            if(!a){
                log_error("Error storing Clear query.");
                return;
            }

            //broadcast pointer to message over Multicast
            while(!spin1_send_mc_packet(myKey, a, WITH_PAYLOAD)){
                log_info("Attempting to send Clear MC packet again.");
                spin1_delay_us(1);
            }

            spin1_msg_free(msg);
            return;
        }
        */

        #ifdef DB_TYPE_KEY_VALUE_STORE

        if(header->cmd == PUT || header->cmd == PULL){
            putPullQuery* p = (putPullQuery*)header;

            //log_info("%s, id %d", p->cmd == PUT ? "PUT" : "PULL", p->id);
            //log_info("  info: %08x, data: %s", p->info, p->data);

            #ifdef DB_SUBTYPE_HASH_TABLE
                    uint32_t h = hash(p->data, k_size_from_info(p->info));

                    h_chipx =((h & 0x00FF0000) >> 16) % CHIP_X_SIZE;
                    h_chipy =((h & 0x0000FF00) >> 8)  % CHIP_Y_SIZE;
                    h_core  =((h & 0x000000FF) % NUMBER_OF_LEAVES) + FIRST_LEAF;
            #else
                if(header->cmd == PUT){
                    if(++h_core > LAST_LEAF){
                        h_core = FIRST_LEAF;
                        if(++h_chipx >= CHIP_X_SIZE){
                            h_chipx = 0;
                            if(++h_chipy >= CHIP_Y_SIZE){
                                h_chipy = 0;
                            }
                        }
                    }
                }
                else{ //PULL

                    if(msg->srce_port == PORT_ETH){ //msg came from host
                        //tell the other root cores to scan
                        set_srce_as_self(msg);

                        set_dest_xyp(msg, 0, 1, 1);
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                        set_dest_xyp(msg, 1, 0, 1);
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                        set_dest_xyp(msg, 1, 1, 1);
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);
                    }

                    //if we run out of root SDRAM, roll over
                    if(currentQueryAddr+sizeof(pullQuery) >=
                        CORE_DATABASE_SIZE_WORDS){
                            currentQueryAddr = startQueryAddr;
                    }

                    address_t a = append(&currentQueryAddr,
                                         p, sizeof(pullQuery));
                    if(!a){
                        log_error("Error storing pullQuery to SDRAM.");
                        continue;
                    }

                    //broadcast pointer to message over Multicast
                    while(!spin1_send_mc_packet(myKey, (uint)a, WITH_PAYLOAD)){
                        log_info("Attempting to send PULL MC packet again.");
                        spin1_delay_us(1);
                    }

                    //spin1_msg_free(msg);
                    continue;
                }
            #endif

            set_dest_xyp(msg, h_chipx, h_chipy, h_core);

            if(spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                log_info("  Sent to (%d,%d,%d)",
                         h_chipx, h_chipy, h_core);
            }
            else {
                log_error("  Unable to send query to (%d,%d,%d)",
                          p->data, h_chipx, h_chipy, h_core);
            }
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
                    write((address_t)newTable, t, sizeof(Table));

                    log_info("  Table '%s'-> %08x", newTable->name, newTable);
                    print_table(newTable);
                }

                revert_src_dest(msg);

                msg->length = sizeof(sdp_hdr_t) + sizeof(Response_hdr);

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
                    continue;
                }
                break;
            case SELECT:;
                log_info("SELECT");
                print_SELECT((selectQuery*)header);

                //store SELECT query message to SDRAM
                //so it can be read by other cores
                address_t a = append(&currentQueryAddr,
                                     (selectQuery*)header,
                                     sizeof(selectQuery));

                if(!a){
                    log_error("Error storing selectQuery to SDRAM.");
                    continue;
                }

                //broadcast pointer to message over Multicast
                while(!spin1_send_mc_packet(myKey, a, WITH_PAYLOAD)){
                    log_info("Attempting to send MC packet again.");
                    spin1_delay_us(1);
                }
                break;
            default:;
                //log_info("[Warning] cmd not recognized: %d with id %d",
                //         header->cmd, header->id);
                break;
        }
        #endif

        // free the message to stop overload
        //spin1_msg_free(msg);
        //sark_free(msg);

       }
       else {
        processing_events = false;
       }
    }
    while (processing_events);
}

void c_main(){
    chipx = (spin1_get_chip_id() & 0xFF00) >> 8;
    chipy = spin1_get_chip_id() & 0x00FF;
    core  = spin1_get_core_id();

    log_info("Initializing Root...");

    if (!initialize_with_MC_key()) {
        rt_error(RTE_SWERR);
    }

    #ifdef DB_TYPE_RELATIONAL
        tables = (Table*) data_region;

        startQueryAddr = data_region + sizeof(Table) * DEFAULT_NUMBER_OF_TABLES;
    #endif
    #ifdef DB_TYPE_KEY_VALUE_STORE
        startQueryAddr = data_region;
    #endif

    currentQueryAddr = startQueryAddr;

    msg_cpies = (sdp_msg_t**)sark_alloc(QUEUE_SIZE, sizeof(sdp_msg_t*));
    for(uint i = 0; i < QUEUE_SIZE; i++){
        msg_cpies[i] = (sdp_msg_t*)sark_alloc(1, sizeof(sdp_hdr_t)+256);
    }

    if(!msg_cpies){
        log_error("Unable to allocate memory for msg_cpies");
        rt_error(RTE_SWERR);
    }

    sdp_buffer = circular_buffer_initialize(QUEUE_SIZE);

    if(!sdp_buffer){
        rt_error(RTE_SWERR);
    }

    //capacitor_buffer = circular_buffer_initialize(200);

    //timer tick in microseconds
    spin1_set_timer_tick(TIMER_PERIOD);

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, 0);
    spin1_callback_on(TIMER_TICK,       update,              1);
    spin1_callback_on(USER_EVENT,       process_requests,    2);

    simulation_run();
}