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

double_linked_list* unreplied_puts;
double_linked_list* unreplied_pulls;

static circular_buffer sdp_buffer;

///////////////////////////////////////////////////////////////////////////////

void send_failed_invalid_spiDBquery(spiDBquery* q){
        sdp_msg_t* message_to_host = create_sdp_header_to_host();

        message_to_host->cmd_rc = q->cmd;
        message_to_host->seq    = q->id;
        message_to_host->arg1   = -1;
        message_to_host->arg2   = 0;
        message_to_host->arg3   = 0; //round trip time

        message_to_host->length = sizeof(sdp_hdr_t) + 16;

        spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
}

//uint32_t*** core_db_current_sizes;

#ifdef DB_HASH_TABLE
    uint32_t hash(uchar* bytes, size_t size){
        uint32_t h = 5381;

        for(uint16_t i = 0; i < size; i++){
            h = ((h << 5) + h) + (bytes[i] ^ (bytes[i] << 28));
        }

        return h;
    }
#else
    uint8_t rrb_chipx = 0;
    uint8_t rrb_chipy = 0;
    uint8_t rrb_core  = ROOT_CORE+1;

    void broadcast(sdp_msg_t* msg){
    for(uint8_t chipx = 0; chipx < CHIP_X_SIZE; chipx++){
        for(uint8_t chipy = 0; chipy < CHIP_Y_SIZE; chipy++){
            for(uint8_t core = FIRST_SLAVE; core <= LAST_SLAVE; core++){
                if(chipx == 0 && chipy == 0 && core == ROOT_CORE){
                    continue; //don't send it to itself
                }

                msg->dest_addr = (chipx << 8) | chipy; //[1 byte x, 1 byte y]
                msg->dest_port = (SDP_PORT << PORT_SHIFT) | core;
                spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
            }
        }
    }
}
#endif

bool send_spiDBquery(spiDBquery* q){

    if(q->k_size == 0 || (q->cmd == PUT && q->v_size == 0)){
        send_failed_invalid_spiDBquery(q);
        return false;
    }

    sdp_msg_t* msg   = create_sdp_header(0, 1); // this is a stub...

    msg->cmd_rc = q->cmd;
    msg->seq    = q->id;

    msg->arg2   = 0;
    msg->arg3   = 0;

    if(q->cmd == PULL){
        q->v_type = 0;
        q->v_size = 0;
    }

    msg->arg1 = to_info(q->k_type, q->k_size, q->v_type, q->v_size);

    memcpy(msg->data, q->k_v, q->k_size + q->v_size);

    msg->length = sizeof(sdp_hdr_t) + 16 + q->k_size + q->v_size;

    #ifdef DB_HASH_TABLE
        switch(q->cmd){
            case PUT:;
            case PULL:;
                // core_db_current_sizes
                uint32_t h = hash(q->k_v, q->k_size);

                //todo simplify this
                uint8_t  chip_id_x = ((h & 0xF0000000) >> 28) % CHIP_X_SIZE;
                uint8_t  chip_id_y = ((h & 0x0F000000) >> 24) % CHIP_Y_SIZE;
                uint8_t  core_id   = (((h & 0x00F80000) >> 19) % CORE_SIZE)
                                                                + FIRST_SLAVE;
                if(chip_id_x == 0 && chip_id_y == 0 && core_id == ROOT_CORE){
                    core_id++; //todo temporary solution
                }

                log_info("Sending (%s) to (%d,%d,%d)",
                         q->k_v, chip_id_x, chip_id_y, core_id);

                //[1 byte x, 1 byte y]
                msg->dest_addr = (chip_id_x << 8) | chip_id_y;
                msg->dest_port = (SDP_PORT << PORT_SHIFT) | core_id;
                msg->arg2      = h; //send hash

                spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                break;
            default:
                break;
        }
    #else
        switch(q->cmd){
            case PUT:
                //rrb stands for Round Robin

                rrb_core++;

                if(rrb_core == ROOT_CORE && rrb_chipx == 0 && rrb_chipy == 0){
                    //root core does not store values, so skip it
                    rrb_core++;
                }

                if(rrb_core > LAST_SLAVE){
                    rrb_core = FIRST_SLAVE;
                    rrb_chipx = (rrb_chipx+1) % CHIP_X_SIZE;

                    if(rrb_chipx == 0){
                        rrb_chipy = (rrb_chipy+1) % CHIP_Y_SIZE;
                    }
                }

                //[1 byte x, 1 byte y]
                msg->dest_addr = (rrb_chipx << 8) | rrb_chipy;
                msg->dest_port = (SDP_PORT << PORT_SHIFT) | rrb_core;

                log_info("Sending PUT to (%d,%d,%d)",
                         rrb_chipx, rrb_chipy, rrb_core);
                //print_msg(msg);

                spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
            case PULL:
                    broadcast(msg);
                    break;
            default:
                    break;
        }
    #endif

    unreplied_query* uq = init_unreplied_query(msg);

    if(q->cmd == PUT){
        push(unreplied_puts,  uq);
    }
    else if(q->cmd == PULL) {
        push(unreplied_pulls,  uq);
        //print_unreplied_queue(unreplied_pulls);
    }

    return true;
}

void send_failed_spiDBquery(unreplied_query* uq){ //source is -1

    sdp_msg_t* message_to_host = create_sdp_header_to_host();

    message_to_host->cmd_rc = uq->msg->cmd_rc;
    message_to_host->seq    = uq->msg->seq;
    message_to_host->arg1   = -1;
    message_to_host->arg2   = 0;
    message_to_host->arg3   = time - uq->time_sent; //round trip time

    message_to_host->length = sizeof(sdp_hdr_t) + 16;

    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
}


void retry_unreplied_entries(double_linked_list* unreplied_queries){
    list_entry* entry = *unreplied_queries->head;
    unreplied_query* uq;

    while(entry != NULL){
        uq = (unreplied_query*)entry->data;

        uq->ticks += TIMER_PERIOD;
        if(uq->ticks >= RETRY_RATE){
            uq->ticks = 0;
            uq->retries++;

            if(uq->retries > MAX_RETRIES){
                log_info("Tried query with id %d, cmd_rc %d too many times.",
                         uq->msg->seq, uq->msg->cmd_rc);

                //todo ineffient linear removal
                remove_from_unreplied_queue(unreplied_queries,uq->msg->seq);
                send_failed_spiDBquery(uq);
            }
            else{
                log_info("Retrying cmd %d, data %s",
                         uq->msg->cmd_rc, uq->msg->data);
                spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT);
            }
        }

        entry = entry->next;
    }
}

/*
void SELECT_entry(uint32_t id){

    uint core = FIRST_SLAVE+1;

    for(uint i = 0; i < 2; i++){
       if(arr_equals(table.fields[i].name, field_name, table.fields[i].name_size)){
         core = FIRST_SLAVE+i; //todo hmmmm
         break;
       }
    }

    sdp_msg_t* msg = create_sdp_header(0,core);//todo
    msg->cmd_rc = PULL;

    msg->seq    = 0; //todo
    msg->arg2   = 0;
    msg->arg3   = 0;

    msg->arg1 = to_info(UINT32, ID_SIZE, 0, 0);

    memcpy(msg->data, id, ID_SIZE);

    msg->length = sizeof(sdp_hdr_t) + 16 + ID_SIZE;
    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
}
*/

Table* table;

void send_INSERT(insertQuery* q){

    sdp_msg_t* msg = create_sdp_header(0,2);//todo
    memcpy(&msg->cmd_rc, q, sizeof(insertQuery));

    msg->length = sizeof(sdp_hdr_t) + sizeof(insertQuery); //todo reduce to table size

    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
}

void send_SELECT(selectQuery* q){
    sdp_msg_t* msg = create_sdp_header(0,2);//todo
    memcpy(&msg->cmd_rc, q, sizeof(selectQuery));

    msg->length = sizeof(sdp_hdr_t) + sizeof(selectQuery); //todo reduce to table size

    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
}

/*
void INSERT_pair(insertQuery* q){
    uint core = FIRST_SLAVE+1;

    for(uint i = 0; i < 2; i++){
       if(arr_equals(table.fields[i].name, q->f_v, table.fields[i].name_size)){
         core = FIRST_SLAVE+1+i; //todo hmmmm
         break;
       }
    }

    log_info("Sending INSERT to CORE >> %d", core);

    sdp_msg_t* msg = create_sdp_header(0,core);//todo
    msg->cmd_rc = PUT;
    msg->seq = 0;//todo

    msg->arg1 = to_info(UINT32, ID_SIZE, STRING, q->value_size);

    memcpy(msg->data,           &q->row_id, ID_SIZE);
    memcpy(&msg->data[ID_SIZE], &q->f_v[q->field_name_size], q->value_size);

    msg->length = sizeof(sdp_hdr_t) + 16 + ID_SIZE + q->value_size;

    //msg->arg2 = 0;

    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
}
*/

void update (uint ticks, uint b){
    use(ticks);
    use(b);

    time += TIMER_PERIOD;

    //todo if test mode
    /*
    if(ticks == 10){
        run_put_tests();
    }
    else if(ticks == 1000){
        tests_summary();
    }
    */

    retry_unreplied_entries(unreplied_puts);
    retry_unreplied_entries(unreplied_pulls);

    //COLUMN BASED
/*    if(time == TIMER_PERIOD * 10 * 10){
        //try to insert ["Tuca", 21]
        log_info("SENDING GET IDS WITH CONDITION");
        get_IDs_with_condition();
    }*/

}

void send_reply_to_host(sdp_msg_t* reply_msg, unreplied_query* uq){

    uint8_t srce_core_id = get_srce_core(reply_msg);

    //[1 byte chip x, 1 byte chip y, 1 byte - core id]
    //chip and core where reply came from
    uint32_t srce = (reply_msg->srce_addr << 8) | srce_core_id;

    sdp_msg_t* message_to_host  = create_sdp_header_to_host();
    message_to_host->seq        = reply_msg->seq;
    message_to_host->arg1       = srce; //where it came from!
    message_to_host->arg3       = time - uq->time_sent; //round trip time

    switch(reply_msg->cmd_rc){
        case PUT_REPLY:;
            message_to_host->cmd_rc = PUT;

            message_to_host->arg2 = 1; //info != 0 means success

            message_to_host->length = sizeof(sdp_hdr_t) + 16;
            break;
        case PULL_REPLY:;
            message_to_host->cmd_rc = PULL;

            if(reply_msg->arg1 == 0){ //reply info equals zero means failure
                message_to_host->arg2 = 0;
                message_to_host->length = sizeof(sdp_hdr_t) + 16;
            }
            else{
                var_type data_type = v_type_from_info(reply_msg->arg1);
                size_t   data_size = v_size_from_info(reply_msg->arg1);

                message_to_host->arg2 = to_info(data_type, data_size, 0, 0);

                memcpy(message_to_host->data, reply_msg->data, data_size);

                message_to_host->length = sizeof(sdp_hdr_t) + 16 + data_size;
            }
            break;
        default:
            return;
    }

    print_msg(message_to_host);

    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
}

void sdp_packet_callback(uint mailbox, uint port) {
    use(port);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }
}

void print_table(Table* t){
    log_info("####### TABLE #######");
    log_info("t->n_cols %d", t->n_cols);
    log_info("t->row_size %d", t->row_size);

    for(uint i = 0; i < 4; i++){
        log_info("t->cols[%d] size: %d, type: %d",
                    i, t->cols[i].size, t->cols[i].type);
    }
}

void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    uint32_t* mailbox_ptr = NULL;
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){

        sdp_msg_t* msg = (sdp_msg_t*)*mailbox_ptr;

        //TODO MUDOOOOOOOOOOOU
        if(msg->srce_port == PORT_ETH){ //coming from host
            //spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);
            //printQuery(query);

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            switch(header->cmd){
                case CREATE_TABLE:;
                    log_info("CREATE");
                    createTableQuery* q = (createTableQuery*) header;
                    print_table(&q->table);
                    memcpy(table, &q->table, sizeof(Table));
                    write(data_region, table, sizeof(Table));
                    break;
                case INSERT_INTO:;
                    log_info("INSERT_INTO");
                    insertQuery* insertQ = (insertQuery*) header;
                    send_INSERT(insertQ);
                    break;
                case SELECT:;
                    log_info("SELECT");
                    selectQuery* selectQ = (selectQuery*) header;
                    send_SELECT(selectQ);
                    break;
                default:;
                    log_info("[Warning] cmd not recognized: %d with id %d",
                             header->cmd, header->id);
                    break;
            }

            /*
            switch(query->cmd){
                case PUT:
                case PULL:
                    send_spiDBquery(query);
                    break;
                case CREATE_TABLE:;
                    createTableQuery* q = (createTableQuery*) &(msg->cmd_rc);
                    write(data_region, &q->table, sizeof(Table));
                    memcpy(table, &q->table, sizeof(Table));
                    break;
                case INSERT_INTO:;
                    insertQuery* query = (insertQuery*) &(msg->cmd_rc);
                    //INSERT_pair(query);
                    break;
                default:
                    log_info("Invalid query from host with cmd = %d", query->cmd);
                    break;
            }
            */
        }
        else{
            //test_message(msg);

            unreplied_query* uq = NULL;

            switch(msg->cmd_rc){
                case PUT_REPLY:;
                    uq = remove_from_unreplied_queue(unreplied_puts, msg->seq);
                    break;
                case PULL_REPLY:;
                    uq = remove_from_unreplied_queue(unreplied_pulls, msg->seq);
                    break;
                default:;
                    sentinel("Received invalid reply with id: %d, cmd_rc: %02x",
                             msg->seq, msg->cmd_rc);
                    print_msg(msg);
                    return;
            }
            check(uq, "Received a reply with unexpected id %d of type %d",
                      msg->seq, msg->cmd_rc);
            if(uq){
                send_reply_to_host(msg, uq);
            }
        }

        // free the message to stop overload
        spin1_msg_free(msg);
    }
}

void c_main(){

    table = (Table*)sark_alloc(1, sizeof(Table));

    log_info("Initializing Root...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    spin1_set_timer_tick(TIMER_PERIOD);

    //Global assignments
    unreplied_puts  = init_double_linked_list();
    unreplied_pulls = init_double_linked_list();

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
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, -1);
    spin1_callback_on(TIMER_TICK,       update,              0);
    spin1_callback_on(USER_EVENT,       process_requests,    1);

    simulation_run();
}