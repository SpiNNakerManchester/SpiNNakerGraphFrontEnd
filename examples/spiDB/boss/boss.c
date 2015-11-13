/***** master.c/master_summary
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
#include "../db-typedefs.h"
#include "../sdram_writer.h"
#include "../sdp_utils.h"
#include <data_specification.h>
#include <sark.h>
#include <circular_buffer.h>
#include "../double_linked_list.h"
#include "../message_queue.h"

#include <debug.h>

#define TIMER_PERIOD 100

// Globals
uint32_t time               = 0; //represents the microseconds

const double_linked_list* unreplied_puts;
const double_linked_list* unreplied_pulls;

const uint16_t board_dimentions_x = 2;
const uint16_t board_dimentions_y = 2;

static circular_buffer sdp_buffer;

void broadcast(sdp_msg_t* msg){
    //todo for loop it

    msg->dest_addr = 0x0001;
    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

    msg->dest_addr = 0x0100;
    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

    msg->dest_addr = 0x0101;
    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
}

uint32_t** chip_current_sizes;

uint8_t x_chip_with_less_data = 0;
uint8_t y_chip_with_less_data = 1;

void send_spiDBquery(spiDBquery* q){

    sdp_msg_t* msg = init_boss_sdp(q);

    unreplied_query* uq = init_unreplied_query(msg);

    switch(q->cmd){
        case PUT:   push(unreplied_puts,  uq);
                    //todo what if it is itself?

                    msg->dest_addr = (x_chip_with_less_data << 8) | y_chip_with_less_data; //[1 byte x, 1 byte y]

                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                    chip_current_sizes[x_chip_with_less_data][y_chip_with_less_data] += 1 + (q->k_size+3)/4 + (q->v_size+3)/4;

                    for(int x=0; x < board_dimentions_x; x++){
                        for(int y=0; y < board_dimentions_y; y++){
                            log_info("chip_current_sizes[x=%d][y=%d] -> %d", x, y, chip_current_sizes[x][y]);
                            if(x == 0 && y == 0){
                                continue;//todo avoid doing it itself for now
                            }

                            if(chip_current_sizes[x][y] < chip_current_sizes[x_chip_with_less_data][y_chip_with_less_data]){
                                x_chip_with_less_data = x;
                                y_chip_with_less_data = y;
                            }
                        }
                    }

                    break;
        case PULL:  push(unreplied_pulls, uq);
                    broadcast(msg);
                    break;
        case CLEAR:;for(int x=0; x < board_dimentions_x; x++){
                        for(int y=0; y < board_dimentions_y; y++){
                            chip_current_sizes[x][y] = 0;
                        }
                    }
                    broadcast(msg);
                    break;
        default:    log_error("Invalid spiDBquery.cmd %d", q->cmd);
                    break;
    }

    //print_unreplied_queue(unreplied_puts);

    //print_msg(uq->msg);

}

void send_failed_spiDBquery(unreplied_query* uq){ //source is -1

    sdp_msg_t* message_to_host = create_sdp_header_to_host();

    message_to_host->cmd_rc = uq->msg->cmd_rc;
    message_to_host->seq    = uq->msg->seq;
    message_to_host->arg1   = -1;
    message_to_host->arg2   = 0;
    message_to_host->arg3   = time - uq->time_sent; //round trip time. todo what unit of measurement is this?

    message_to_host->length = sizeof(sdp_hdr_t) + 16;

    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
}

void update (uint ticks, uint b){
    time += TIMER_PERIOD;

    return; //for now.... TODO

    if(ticks % 1500 == 0){ //retry pull

        list_entry* entry = *unreplied_pulls->head;

        while(entry != NULL){
            unreplied_query* uq = (unreplied_query*)entry->data;

            if(uq->retries >= MAX_RETRIES){
                log_info("PULL not found [time: %d, rtt: %d, retries: %d]",
                          time, time - uq->time_sent, uq->retries);
                remove_from_unreplied_queue(unreplied_pulls,uq->msg->seq);
                send_failed_spiDBquery(uq);
            }
            else{
                uq->retries++;
                broadcast_pull(uq);
            }

            entry = entry->next;
        }
    }
    else if(ticks % 1500 == 800){ //retry put

        list_entry* entry = *unreplied_puts->head;

        while(entry != NULL){
            unreplied_query* uq = (unreplied_query*)entry->data;
            uq->retries++;

            if(uq->retries >= MAX_RETRIES){
                log_info("Tried sending PUT id %d too many times. Removing from queue", uq->msg->seq);
                remove_from_unreplied_queue(unreplied_puts,uq->msg->seq); //todo ineffient removing here like this
                send_failed_spiDBquery(uq);
            }
            else{
                uq->retries++;
                spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT); //message, timeout
            }

            entry = entry->next;
        }

    }
}

void printQuery(spiDBquery* q){
  log_info("=============================================");
  log_info("=================== QUERY ===================");
  log_info("  id:        %08x", q->id);
  log_info("  cmd:       %04x -> %s", q->cmd, q->cmd == PUT ? "PUT" : "PULL");
  log_info("                                             ");
  log_info("  k_type:    %04x", q->k_type);
  log_info("  k_size:    %04x", q->k_size);
  log_info("                                             ");
  log_info("  v_type:    %04x", q->v_type);
  log_info("  v_size:    %04x", q->v_size);
  log_info("                                             ");
  log_info("  k_v:       %s", q->k_v);
  log_info("=============================================");
}

void send_successful_spiDBqueryReply(sdp_msg_t* reply_msg, unreplied_query* uq){

    uint8_t srce_core_id = reply_msg->srce_port & 0x1F;

    //[1 byte chip x, 1 byte chip y, 1 byte - core id]
    uint32_t srce = (reply_msg->srce_addr << 8) | srce_core_id; //chip and core where reply came from

    sdp_msg_t* message_to_host = create_sdp_header_to_host();

    message_to_host->seq    = reply_msg->seq;

    message_to_host->arg1   = srce; //where it came from!
    message_to_host->arg3   = time - uq->time_sent; //round trip time. todo what unit of measurement is this?

    switch(reply_msg->cmd_rc){
        case PUT_REPLY:;    message_to_host->cmd_rc = PUT;

                            message_to_host->arg2 = 0; //info

                            message_to_host->length = sizeof(sdp_hdr_t) + 16;
                            break;
        case PULL_REPLY:;   message_to_host->cmd_rc = PULL;

                            message_to_host->arg2 = to_info1(reply_msg->arg1, reply_msg->arg2); //data type & size

                            uint32_t data_size = reply_msg->arg2;

                            memcpy(message_to_host->data, reply_msg->data, data_size);

                            message_to_host->length = sizeof(sdp_hdr_t) + 16 + data_size;
                            break;
        default:            return;
    }

    //uint status = spin1_int_disable();
    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
    //spin1_mode_restore(status);
}

void sdp_packet_callback(uint mailbox, uint port) {
    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, mailbox)) {
        spin1_trigger_user_event(0, 0);
    }
}

void process_requests(uint arg0, uint arg1){

    uint32_t* mailbox_ptr;
    while(circular_buffer_get_next(sdp_buffer, mailbox_ptr)){

        sdp_msg_t* msg = (sdp_msg_t*) (*mailbox_ptr);

        if(msg->srce_port == PORT_ETH){ //coming from host
            spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);
            printQuery(query);
            send_spiDBquery(query);
        }
        else{
            unreplied_query* uq = NULL;

            uint status;

            switch(msg->cmd_rc){
                case PUT_REPLY:;    uq = remove_from_unreplied_queue(unreplied_puts, msg->seq);

                                    if(!uq){
                                        log_info("Received a PUT_REPLY with unexpected id %d", msg->seq);
                                        log_info("Unreplied puts is...");
                                        print_unreplied_queue(unreplied_puts);
                                    break;}

                                    log_info("Received a PUT_REPLY [id: %d, time: %d, rtt: %d, retries: %d]",
                                              uq->msg->seq, time, time - uq->time_sent, uq->retries);

                                    send_successful_spiDBqueryReply(msg, uq);

                                    //print_unreplied_queue(unreplied_puts);
                                    break;

                case PULL_REPLY:;   uq = remove_from_unreplied_queue(unreplied_pulls, msg->seq);

                                    if(!uq){
                                        log_info("Received a PULL_REPLY with unexpected id %d", msg->seq);
                                        log_info("Unreplied pulls is...");
                                        print_unreplied_queue(unreplied_pulls);
                                    break;}

                                    log_info("Received a PULL_REPLY [id: %d, time: %d, rtt: %d, retries: %d]",
                                              uq->msg->seq, time, time - uq->time_sent, uq->retries);

                                    send_successful_spiDBqueryReply(msg, uq);

                                    break;
                default:;           log_info("Received invalid reply with id: %d, cmd_rc: %02x", msg->seq, msg->cmd_rc);
                                    print_msg(msg);
                                    break;
            }

        }

        // free the message to stop overload
        spin1_msg_free(msg);

        //spin1_mode_restore(status);
    }
}

void c_main()
{
    log_info("Initializing Boss...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to 100 micro seconds
    spin1_set_timer_tick(TIMER_PERIOD);

    //Global assignments
    unreplied_puts  = init_double_linked_list();
    unreplied_pulls = init_double_linked_list();

    sdp_buffer = circular_buffer_initialize(100); //todo size...

    chip_current_sizes = (uint32_t**) sark_alloc(board_dimentions_x, sizeof(uint32_t*));
    for(int x = 0; x < board_dimentions_x; x++){
        chip_current_sizes[x] = (uint32_t*) sark_alloc(board_dimentions_y, sizeof(uint32_t));

        for(int y = 0; y < board_dimentions_y; y++){
            chip_current_sizes[x][y] = 0;
        }
    }

    // register callbacks
    spin1_callback_on(SDP_PACKET_RX,    sdp_packet_callback, -1);
    spin1_callback_on(TIMER_TICK,       update,              0);
    spin1_callback_on(USER_EVENT,       process_requests,    1);

    simulation_run();
}