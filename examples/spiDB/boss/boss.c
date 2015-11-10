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
#include "../double_linked_list.h"
#include "../message_queue.h"

#include <debug.h>

// Globals
uint32_t time               = 0;

const double_linked_list* unreplied_puts;
const double_linked_list* unreplied_pulls;


uint32_t current_message_id = 0;

void broadcast_pull(unreplied_query* uq){
    //todo for loop it
    uq->msg->dest_addr = 0x0001;
    spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT); //message, timeout

    uq->msg->dest_addr = 0x0100;
    spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT); //message, timeout

    uq->msg->dest_addr = 0x0101;
    spin1_send_sdp_msg(uq->msg, SDP_TIMEOUT); //message, timeout
}

void send_spiDBquery(spiDBquery* q){

    sdp_msg_t* msg = init_boss_sdp(q,current_message_id);

    unreplied_query* uq = init_unreplied_query(msg);

    switch(q->cmd){
        case PUT:   push(unreplied_puts,  uq);
                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                    break;
        case PULL:  push(unreplied_pulls, uq);
                    broadcast_pull(uq);

                    break;
        default:    log_error("Invalid spiDBquery.cmd %d", q->cmd);
                    break;
    }

    //print_unreplied_queue(unreplied_puts);

    //print_msg(uq->msg);

    current_message_id++;
}

void send_failed_spiDBquery(unreplied_query* uq){ //source is -1

    sdp_msg_t* message_to_host = create_sdp_header_to_host();

    message_to_host->cmd_rc = uq->msg->cmd_rc;
    message_to_host->seq    = uq->msg->seq;
    message_to_host->arg1   = -1;
    message_to_host->arg2   = 0;
    message_to_host->arg3   = time - uq->time_sent; //round trip time. todo what unit of measurement is this?

    message_to_host->length = sizeof(sdp_hdr_t) + 16;

    print_msg(message_to_host);

    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout
}

void update (uint ticks, uint b){
    time++;

    if(ticks % 15 == 0){ //retry pull

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
    else if(ticks % 15 == 8){ //retry put

        list_entry* entry = *unreplied_puts->head;

        while(entry != NULL){
            unreplied_query* uq = (unreplied_query*)entry->data;
            uq->retries++;

            if(uq->retries >= MAX_RETRIES){
                log_info("Tried sending PUT id %d too many times. Removing from queue", uq->msg->seq);
                remove_from_unreplied_queue(unreplied_puts,uq->msg->seq); //todo ineffient removing here like this
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
  log_info("  cmd:       %04x -> %s", q->cmd, q->cmd == PUT ? "PUT" : "PULL");
  log_info("                                             ");
  log_info("  k_type:    %04x", q->k_type);
  log_info("  k_size:    %04x", q->k_size);
  log_info("  k:         %s",   q->k);
  log_info("                                             ");
  log_info("  v_type:    %04x", q->v_type);
  log_info("  v_size:    %04x", q->v_size);
  log_info("  v:         %s",   q->v);
  log_info("=============================================");
}


void send_successful_spiDBqueryReply(sdp_msg_t* reply_msg, unreplied_query* uq){

    uint32_t srce_core_id = reply_msg->srce_port & 0x1F;

    //[2 bytes - chip id, 2 bytes - core id]
    //todo PORT_SHIFT on the 1f
    uint32_t srce = (reply_msg->srce_addr << 16) | srce_core_id; //chip and core where reply came from

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

    print_msg(message_to_host);

    spin1_send_sdp_msg(message_to_host, SDP_TIMEOUT); //message, timeout

}

void sdp_packet_callback(uint mailbox, uint port) {

    use(port);

    sdp_msg_t* msg = (sdp_msg_t*) mailbox;

    if(msg->srce_port == PORT_ETH){ //coming from host
        spiDBquery* query = (spiDBquery*) &(msg->cmd_rc);

        log_info("Received spiDBquery from host:");
        printQuery(query);

        send_spiDBquery(query);
    }
    else{
        unreplied_query* uq = NULL;


        switch(msg->cmd_rc){
            case PUT_REPLY:;    uq = remove_from_unreplied_queue(unreplied_puts, msg->seq);
                                if(!uq){break;}

                                log_info("Received a PUT_REPLY [time: %d, rtt: %d, retries: %d]",
                                          time, time - uq->time_sent, uq->retries);

                                send_successful_spiDBqueryReply(msg, uq);

                                //print_unreplied_queue(unreplied_puts);
                                break;

            case PULL_REPLY:;   uq = remove_from_unreplied_queue(unreplied_pulls, msg->seq);
                                if(!uq){break;}
                                log_info("Received a PULL_REPLY [time: %d, rtt: %d, retries: %d]",
                                          time, time - uq->time_sent, uq->retries);

                                send_successful_spiDBqueryReply(msg, uq);

                                break;
            default:;       break;
        }

        if(!uq){
            log_info("Received an unexpected unreplied_query* %08x", uq);
        }
    }

    // free the message to stop overload
    spin1_msg_free(msg);
}

void _user_event_callback(uint unused0, uint unused1){
    log_info("Received User Event message");
}

void _multicast_packet_received_callback(uint key, uint payload) {
    log_info("Received Multicast message");
}

void c_main()
{
    log_info("Initializing Boss...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to 100ms
    spin1_set_timer_tick(100);

    //Global assignments
    unreplied_puts  = init_double_linked_list();
    unreplied_pulls = init_double_linked_list();

    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 1);
    spin1_callback_on (SDP_PACKET_RX, sdp_packet_callback, -1);

    //spin1_callback_on (MCPL_PACKET_RECEIVED, _multicast_packet_received_callback, 0);
    //spin1_callback_on (MC_PACKET_RECEIVED, _multicast_packet_received_callback, 0);
    //spin1_callback_on(DMA_TRANSFER_DONE, _dma_complete_callback, 0);
    //spin1_callback_on(USER_EVENT, _user_event_callback, 0);

    simulation_run();
}