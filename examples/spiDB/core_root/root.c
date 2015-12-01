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
#include "../sdram_writer.h"
#include "../sdp_utils.h"
#include <data_specification.h>
#include <simulation.h>
#include <sark.h>
#include <circular_buffer.h>
#include "../double_linked_list.h"
#include "../message_queue.h"
#include "unit_tests/root_put_tests.c"

#include <debug.h>

#define TIMER_PERIOD 100

// Globals
uint32_t time               = 0; //represents the microseconds

double_linked_list* unreplied_puts;
double_linked_list* unreplied_pulls;

static circular_buffer sdp_buffer;

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

uint32_t*** core_db_current_sizes;

uint8_t x_chip_with_less_data = 0;
uint8_t y_chip_with_less_data = 1;

uint32_t hash(uchar* bytes, size_t size){
    uint32_t h = 5381;

    for(uint16_t i = 0; i < size; i++){
        h = ((h << 5) + h) + (bytes[i] ^ (bytes[i] << 28));
    }

    return h;
}

uint8_t rrb_chipx = 0;
uint8_t rrb_chipy = 0;
uint8_t rrb_core  = 2;

void send_spiDBquery(spiDBquery* q){

    sdp_msg_t* msg = init_boss_sdp(q);

    #ifdef DB_HASH_TABLE
        switch(q->cmd){
            case PUT:;
            case PULL:;
                        // core_db_current_sizes
                        uint32_t h = hash(q->k_v, q->k_size);

                        uint8_t  chip_id_x = ((h & 0xF0000000) >> 28) % CHIP_X_SIZE;
                        uint8_t  chip_id_y = ((h & 0x0F000000) >> 24) % CHIP_Y_SIZE;
                        uint8_t  core_id   = (((h & 0x00F80000) >> 19) % CORE_SIZE) + FIRST_SLAVE;

                        if(chip_id_x == 0 && chip_id_y == 0 && core_id == ROOT_CORE){
                            core_id++; //todo temporary solution
                        }

                        log_info("Sending (%s) to (%d,%d,%d)", q->k_v, chip_id_x, chip_id_y, core_id);

                        msg->dest_addr = (chip_id_x << 8) | chip_id_y; //[1 byte x, 1 byte y]
                        msg->dest_port = (SDP_PORT << PORT_SHIFT) | core_id;
                        msg->arg2      = h; //send hash

                        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                        break;
            default:    break;
        }
    #else
        switch(q->cmd){
            case PUT:
                        /*
                        rrb_core = (rrb_core+1 % LAST_SLAVE) + FIRST_SLAVE;

                        if(rrb_core == FIRST_SLAVE){
                            rrb_chipx = (rrb_chipx+1) % CHIP_X_SIZE;

                            if(rrb_chipx == 0){
                                rrb_chipy = (rrb_chipy+1) % CHIP_Y_SIZE;
                            }
                        }
                        */

                        msg->dest_addr = (rrb_chipx << 8) | rrb_chipy; //[1 byte x, 1 byte y]
                        msg->dest_port = (SDP_PORT << PORT_SHIFT) | rrb_core;

                        log_info("Sending PUT to (%d,%d,%d)", rrb_chipx, rrb_chipy, rrb_core);
                        print_msg(msg);
                        log_info("-------------------");

                        spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
            case PULL:
                        broadcast(msg);
                        break;
            default:    break;
        }

    #endif

    unreplied_query* uq = init_unreplied_query(msg);

    if(q->cmd == PUT){
        push(unreplied_puts,  uq);
    }
    else if(q->cmd == PULL) {
        push(unreplied_pulls,  uq);
    }

    // free the message to stop overload
    //spin1_msg_free(msg);
    /*
        case CLEAR:;
                    for(int x=0; x < board_dimentions_x; x++){
                        for(int y=0; y < board_dimentions_y; y++){
                            chip_current_sizes[x][y] = 0;
                        }
                    }
                    broadcast(msg);

                    break;
        default:    log_error("Invalid spiDBquery.cmd %d", q->cmd);
                    break;
    */

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

void update (uint ticks, uint b){
    use(b);

    time += TIMER_PERIOD;

    //if TEST MODE!!!! todo
    if(ticks == 10){
        run_put_tests();
    }
    else if(ticks == 1000){
        tests_summary();
    }

    list_entry* entry = *unreplied_puts->head;

    while(entry != NULL){
        unreplied_query* uq = (unreplied_query*)entry->data;

        uq->ticks++;
        if(uq->ticks % 100 == 0){
            uq->retries++;

            if(uq->retries > MAX_RETRIES+10){
                //log_info("Tried sending PUT id %d too many times. Removing from queue", uq->msg->seq);
                remove_from_unreplied_queue(unreplied_puts,uq->msg->seq); //todo ineffient removing here like this
                send_failed_spiDBquery(uq);
            }
            else{
                //log_info("Retrying cmd %d, data %s", uq->msg->cmd_rc, uq->msg->data);
                //print_msg(uq->msg);
                spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT); //message, timeout
            }
        }

        entry = entry->next;
    }

    entry = *unreplied_pulls->head;

    while(entry != NULL){
        unreplied_query* uq = (unreplied_query*)entry->data;

        uq->ticks++;
        if(uq->ticks % 100 == 0){
            uq->retries++;

            if(uq->retries > MAX_RETRIES+10){
                //log_info("Tried sending PULL id %d too many times. Removing from queue", uq->msg->seq);
                remove_from_unreplied_queue(unreplied_pulls,uq->msg->seq); //todo ineffient removing here like this
                send_failed_spiDBquery(uq);
            }
            else{
                //log_info("Retrying cmd %d, data %s", uq->msg->cmd_rc, uq->msg->data);
                //print_msg(uq->msg);
                spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT); //message, timeout
            }
        }

        entry = entry->next;
    }

}

void send_successful_spiDBqueryReply(sdp_msg_t* reply_msg, unreplied_query* uq){

    uint8_t srce_core_id = get_srce_core(reply_msg);

    //[1 byte chip x, 1 byte chip y, 1 byte - core id]
    uint32_t srce = (reply_msg->srce_addr << 8) | srce_core_id; //chip and core where reply came from

    sdp_msg_t* message_to_host = create_sdp_header_to_host();

    message_to_host->seq    = reply_msg->seq;

    message_to_host->arg1   = srce; //where it came from!
    message_to_host->arg3   = time - uq->time_sent; //round trip time. todo what unit of measurement is this?

    switch(reply_msg->cmd_rc){
        case PUT_REPLY:;
                            message_to_host->cmd_rc = PUT;

                            message_to_host->arg2 = 0; //info

                            message_to_host->length = sizeof(sdp_hdr_t) + 16;
                            break;
        case PULL_REPLY:;
                            message_to_host->cmd_rc = PULL;

                            var_type data_type = v_type_from_info(reply_msg->arg1);
                            uint32_t data_size = v_size_from_info(reply_msg->arg1);

                            message_to_host->arg2 = to_info(data_type, data_size, 0, 0); //value type & size

                            memcpy(message_to_host->data, reply_msg->data, data_size);

                            message_to_host->length = sizeof(sdp_hdr_t) + 16 + data_size;
                            break;
        default:            return;
    }

    //print_msg(message_to_host);

    //uint status = spin1_int_disable();
    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
    //spin1_mode_restore(status);
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

        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        if(msg->srce_port == PORT_ETH){ //coming from host
            spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);
            printQuery(query);
            send_spiDBquery(query);
        }
        else{
            test_message(msg);

            unreplied_query* uq = NULL;

            switch(msg->cmd_rc){
                case PUT_REPLY:;
                    uq = remove_from_unreplied_queue(unreplied_puts, msg->seq);

                    check(uq, "Received a PUT_REPLY with unexpected id %d", msg->seq);
                    //if(!uq){print_unreplied_queue(unreplied_puts);break;}

                    //log_info("Received a PUT_REPLY [id: %d, time: %d, rtt: %d, retries: %d]",
                    //          uq->msg->seq, time, time - uq->time_sent, uq->retries);

                    send_successful_spiDBqueryReply(msg, uq);
                    break;

                case PULL_REPLY:;
                    uq = remove_from_unreplied_queue(unreplied_pulls, msg->seq);

                    check(uq, "Received a PULL_REPLY with unexpected id %d", msg->seq);
                    //if(!uq){print_unreplied_queue(unreplied_pulls);break;}

                    //log_info("Received a PULL_REPLY [id: %d, time: %d, rtt: %d, retries: %d]",
                    //          uq->msg->seq, time, time - uq->time_sent, uq->retries);

                    send_successful_spiDBqueryReply(msg, uq);

                    break;
                default:;
                    //sentinel("Received invalid reply with id: %d, cmd_rc: %02x", msg->seq, msg->cmd_rc);
                    //print_msg(msg);
                    break;
            }

        }

        // free the message to stop overload
        spin1_msg_free(msg);

        //spin1_mode_restore(status);
    }
}

void c_main(){
    log_info("Initializing Root...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to 100 micro seconds
    spin1_set_timer_tick(TIMER_PERIOD);

    //Global assignments
    unreplied_puts  = init_double_linked_list();
    unreplied_pulls = init_double_linked_list();

    sdp_buffer = circular_buffer_initialize(100);

    core_db_current_sizes = (size_t***) sark_alloc(CHIP_X_SIZE, sizeof(size_t**));

    for(int x = 0; x < CHIP_X_SIZE; x++){
        core_db_current_sizes[x] = (size_t**) sark_alloc(CHIP_Y_SIZE, sizeof(size_t*));

        for(int y = 0; y < CHIP_Y_SIZE; y++){
            core_db_current_sizes[x][y] = (size_t*) sark_alloc(CORE_SIZE, sizeof(size_t));

            for(int c = 0; c < CORE_SIZE; c++){
                 core_db_current_sizes[x][y][c] = 0;
            }
        }
    }

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, -1);
    spin1_callback_on(TIMER_TICK,       update,              0);
    spin1_callback_on(USER_EVENT,       process_requests,    1);

    simulation_run();
}