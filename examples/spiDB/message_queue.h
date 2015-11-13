
#ifndef __MESSAGE_QUEUE_H__
#define __MESSAGE_QUEUE_H__

#include "double_linked_list.h"
#include "db-typedefs.h"

typedef struct unreplied_query{
    uint8_t     retries;
    uint32_t    time_sent;

    sdp_msg_t*  msg;
} unreplied_query;

extern uint32_t time;

sdp_msg_t* init_boss_sdp(spiDBquery* q){

    sdp_msg_t* msg   = create_sdp_header(0, 1); // chip 0, core 1 (master)

    msg->cmd_rc = q->cmd;
    msg->seq    = q->id;

    msg->arg2   = 0;
    msg->arg3   = 0;

    switch(q->cmd){
        case PUT:;  msg->arg1 = to_info2(q->k_type, q->k_size, q->v_type, q->v_size);

                    memcpy(msg->data, q->k_v, q->k_size + q->v_size);
                    //memcpy(&msg->data[q->k_size], q->v, q->v_size);

                    msg->length = sizeof(sdp_hdr_t) + 16 + q->k_size + q->v_size;

                    break;
        case PULL:; msg->arg1 = to_info1(q->k_type, q->k_size);

                    memcpy(msg->data, q->k_v, q->k_size);

                    msg->length = sizeof(sdp_hdr_t) + 16 + q->k_size;

                    break;
        case CLEAR:;msg->arg1 = 0;
                    break;
        default:    return NULL;
                    break;
    }

    return msg;
}

unreplied_query* init_unreplied_query(sdp_msg_t* msg){
    unreplied_query* uq = (unreplied_query*) sark_alloc(1, sizeof(unreplied_query));
    uq->retries      = 0;
    uq->time_sent    = time;
    uq->msg          = msg;

    return uq;
}
/*
unreplied_query* init_unreplied_query_from_msg(sdp_msg_t msg){
    unreplied_query* q = (unreplied_query*) sark_alloc(1, sizeof(unreplied_query));
    q->retries      = 0;
    q->cmd          = msg.cmd_rc;
    q->message_id   = msg.seq;
    q->info         = msg.arg1;
    q->data         = msg.arg2;
    q->time_sent    = time;
    return q;
}

unreplied_query* init_unreplied_query(interChipCommand cmd, uint32_t message_id, uint32_t info, void* data){
    unreplied_query* q = (unreplied_query*) sark_alloc(1, sizeof(unreplied_query));
    q->retries      = 0;
    q->cmd          = cmd;
    q->message_id   = message_id;
    q->info         = info;
    q->data         = data;
    q->time_sent    = time;
    return q;
}*/

unreplied_query* remove_from_unreplied_queue(double_linked_list* queue, uint32_t message_id){

    list_entry* entry = *queue->head;

    while(entry != NULL){
        unreplied_query* q = (unreplied_query*)entry->data;

        if(q->msg->seq == message_id){

          if(*queue->head == entry){
            *queue->head = entry->next;
          }

          if(*queue->tail == entry){
            *queue->tail = entry->prev;
          }

          if(entry->prev != NULL){ entry->prev->next = entry->next; }
          if(entry->next != NULL){ entry->next->prev = entry->prev; }

          queue->size--;
          return q;
        }

        entry = entry->next;
    }

    return NULL;
}

void print_unreplied_queue(double_linked_list* queue){

    list_entry* entry = *queue->head;

    while(entry != NULL){
        unreplied_query* q = (unreplied_query*)entry->data;
        log_info("[id: %d, retries: %d]", q->msg->seq, q->retries);
        entry = entry->next;
    }
}

// ############################################################################################################

#define RECENT_MESSAGE_CACHE_TTL 10

typedef struct recently_received_query{

    uint32_t message_id;
    uint32_t ttl; //time to live

} recently_received_query;

recently_received_query* init_recently_received_query(uint32_t message_id){
    recently_received_query* q = (recently_received_query*) sark_alloc(1, sizeof(recently_received_query));
    q->ttl          = RECENT_MESSAGE_CACHE_TTL;
    q->message_id   = message_id;
    return q;
}

bool is_duplicate_query(double_linked_list* queue, uint32_t message_id){
    list_entry* entry = *queue->head;

    while(entry != NULL){
        recently_received_query* q = (recently_received_query*)entry->data;

        if(message_id == q->message_id){
            return true;
        }
        entry = entry->next;
    }

    return false;
}

void age_recently_received_queries(double_linked_list* queue){

    if(queue->size > 0){
       list_entry* entry = *queue->tail;

        while(entry != NULL){
            recently_received_query* q = (recently_received_query*)entry->data;
            q->ttl--;

            if(q->ttl <= 0){
                queue->size--;
                *queue->tail = entry->prev; //move tail
                (*queue->tail)->next = NULL; //kill todo free?
            }

            entry = entry->prev;
        }

    }
}

void print_recent_queries_queue(double_linked_list* queue){

    list_entry* entry = *queue->head;

    while(entry != NULL){
        recently_received_query* q = (recently_received_query*)entry->data;
        log_info("[id: %d, ttl: %d]", q->message_id, q->ttl);
        entry = entry->next;
    }
}

#endif





