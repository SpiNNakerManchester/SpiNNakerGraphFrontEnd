/***** master.c/master_summary
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
#include "common-typedefs.h"
#include "../db-typedefs.h"
#include "../memory_utils.h"
#include "../sdp_utils.h"
#include <data_specification.h>
#include <simulation.h>
#include <sark.h>
#include <circular_buffer.h>
#include "../double_linked_list.h"
#include "../message_queue.h"
//#include "unit_tests/root_put_tests.c"

#include <debug.h>

#define TIMER_PERIOD 100
#define RETRY_RATE   TIMER_PERIOD << 4

#define ID_SIZE 4

// Globals
uint32_t time = 0; //represents the microseconds since start


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

uchar chipx;
uchar chipy;
uchar core;

Table* table;

address_t currentQueryAddr;

void update (uint ticks, uint b){
    use(ticks);
    use(b);

    time += TIMER_PERIOD;

    /*
    if(time % 10000000 == 0){
        send_first_value(1,2);
        //spin1_exit(0);
    }
    */
}

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }
}

void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    uint32_t* mailbox_ptr = NULL;
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){

        sdp_msg_t* msg = (sdp_msg_t*)*mailbox_ptr;

        if(msg->srce_port == PORT_ETH){ //coming from host
            //spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);
            //printQuery(query);

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            #ifdef DB_TYPE_KEY_VALUE_STORE
            switch(header->cmd){
                case PUT:;
                    putQuery* putQ = (putQuery*) header;

                    #ifdef DB_SUBTYPE_HASH_TABLE
                        uint32_t h = hash(putQ->k_v,
                                          k_size_from_info(putQ->info));

                        uchar h_chipx =  (h & 0x00FF0000 >> 16) % CHIP_X_SIZE;
                        uchar h_chipy =  (h & 0x0000FF00 >> 8)  % CHIP_Y_SIZE;
                        uchar h_core  = ((h & 0x000000FF)       % CORE_SIZE)
                                            + FIRST_SLAVE;
                    #else

                    set_dest_xyp(msg, h_chipx, h_chipy, h_core);

                    #endif


                    break;
                case PULL:;

                    break;

            }
            #endif
            #ifdef DB_TYPE_RELATIONAL

            switch(header->cmd){
                case CREATE_TABLE:;
                    log_info("CREATE");
                    createTableQuery* q = (createTableQuery*) header;
                    Table* t = &q->table;

                    uint32_t row_size = 0;
                    for(uint32_t i = 0; i < t->n_cols; i++){
                        //round up to the closest power of 4
                        //as Spinnaker is word aligned
                        t->cols[i].size = ((t->cols[i].size + 3) / 4) * 4; //& 0xFFFFFFFD; //unset the first 2 bits
                        row_size += t->cols[i].size;
                    }
                    t->row_size = row_size;

                    write(data_region, t, sizeof(Table));
                    table = (Table*)data_region;

                    log_info("Table created in address %08x", table);
                    print_table(table);

                    revert_src_dest(msg);

                    msg->length = sizeof(sdp_hdr_t) + 9;

                    Response* response = (Response*)&msg->cmd_rc;
                    response->id  = q->id;
                    response->cmd = q->cmd;
                    response->success = table ? true : false;
                    response->x = chipx;
                    response->y = chipy;
                    response->p = core;

                    spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                    break;
                case INSERT_INTO:;
                    insertEntryQuery* insertE = (insertEntryQuery*) header;
                    Entry e = insertE->e;

                    uint32_t dest_core = (e.row_id % 11) + FIRST_LEAF;
                    log_info("INSERT_INTO (id:%d) -> core %d", e.row_id, dest_core);

                    set_dest_chip(msg,spin1_get_chip_id());//same chip
                    set_dest_core(msg,dest_core);
                    spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                    break;
                case SELECT:;
                    log_info("SELECT");

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

                    log_info("Sent MC packet.");

                    /*
                    for(uint32_t i = FIRST_LEAF; i <= LAST_LEAF; i++){
                        sdp_msg_t* forward_msg = (sdp_msg_t*)sark_alloc(1,sizeof(sdp_msg_t));

                        sark_msg_cpy (forward_msg, msg);

                        set_dest_core(forward_msg,i);

                        uint sent = spin1_send_sdp_msg(forward_msg, SDP_TIMEOUT);
                        if(!sent){
                            log_info("%%%% FAILED TO SEND SDP QUERY TO >> %d", i);
                        }
                        else{
                            log_info("Successfully sent to %d (d=%08x)", i, forward_msg->dest_port);
                        }
                        spin1_msg_free(forward_msg);
                    }
                    */

                    //selectQuery* selectQ = (selectQuery*) header;
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

    table = (Table*)sark_alloc(1, sizeof(Table));

    currentQueryAddr = data_region + sizeof(Table);

    spin1_set_timer_tick(TIMER_PERIOD);

    //Global assignments
    //unreplied_puts  = init_double_linked_list();
    //unreplied_pulls = init_double_linked_list();

    sdp_buffer = circular_buffer_initialize(100);

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