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
//#include "eieio_interface.h"
//#include "reverse_iptag_multicast_source.c"

#include <debug.h>

// Globals
uint32_t time               = 0;

const double_linked_list* unreplied_puts;
const double_linked_list* unreplied_pulls;

void update (uint ticks, uint b){
    time++;
}

uint32_t current_message_id = 0;

void send_spiDBquery(spiDBquery* q){

    sdp_msg_t* msg = init_boss_sdp(q,current_message_id);

    unreplied_query* uq = init_unreplied_query(msg);

    switch(q->cmd){
        case PUT:   push(unreplied_puts,  uq);
                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                    break;
        case PULL:  push(unreplied_pulls, uq);

                    //todo for loop it
                    uq->msg->dest_addr = 0x0001;
                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                    uq->msg->dest_addr = 0x0100;
                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout

                    uq->msg->dest_addr = 0x0101;
                    spin1_send_sdp_msg(msg, SDP_TIMEOUT); //message, timeout
                    break;
        default:    log_error("hmmm invalid q->cmd %d", q->cmd);
                    break;
    }

    //print_unreplied_queue(unreplied_puts);

    //print_msg(uq->msg);



    current_message_id++;
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
        print_msg(msg);

        unreplied_query* uq = NULL;

        switch(msg->cmd_rc){
            case PUT_REPLY:;    uq = remove_from_unreplied_queue(unreplied_puts, msg->seq);
                                if(!uq){break;}

                                log_info("Received a PUT_REPLY [time: %d, rtt: %d, retries: %d]",
                                          time, time - uq->time_sent, uq->retries);
                                //print_unreplied_queue(unreplied_puts);
                                break;
            case PULL_REPLY:;   uq = remove_from_unreplied_queue(unreplied_pulls, msg->seq);
                                if(!uq){break;}
                                log_info("Received a PULL_REPLY [time: %d, rtt: %d, retries: %d]",
                                          time, time - uq->time_sent, uq->retries);
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
    log_info("Initializing Master...");

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