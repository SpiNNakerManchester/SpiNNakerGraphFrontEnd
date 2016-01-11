#ifndef __SCAN_H__
#define __SCAN_H__

#include "../db-typedefs.h"
#include "../memory_utils.h"
#include <debug.h>

extern Table* table;
extern uchar chipx;
extern uchar chipy;
extern uchar core;
extern uint32_t myId;
extern uint32_t rows_in_this_core;

sdp_msg_t* send_response_msg(selectQuery* sel, uint32_t row, uint32_t col_index, uint32_t p, uchar* values){
    /*
    typedef struct Entry{
        uint32_t row_id;
        uchar    col_name[16];
        size_t   size;
        uchar    value[256];
    } Entry;
    */

    sdp_msg_t* msg = create_sdp_header_to_host();

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = sel->id;
    r->cmd = sel->cmd;
    r->success = true;
    r->x = chipx;
    r->y = chipy;
    r->p = core;

    Entry* e = &(r->entry);

    e->row_id = myId << 24 | row;
    sark_word_cpy(e->col_name, table->cols[col_index].name, 16);
    e->size   = strlen(&values[p]); //todo how about non-Strings??
    sark_word_cpy(e->value, &values[p], e->size);

    log_info("(%d) %s -> %s", e->row_id, e->col_name, e->value);
                                  //4 + 16 + 4
    msg->length = sizeof(sdp_hdr_t) + 12 + 24 + e->size;

    spin1_send_sdp_msg(msg, SDP_TIMEOUT);

    return msg;
}


void scan_ids(address_t addr, selectQuery* sel){

    if(!table){
        return;
    }

    size_t row_size_words = (table->row_size + 3) >> 2;
    size_t n_cols         = table->n_cols;

    //print_table(table);

    /*

    Condition condition = sel->where.condition;

    Operand  left  = condition.left;
    Operand  right = condition.right;

    size_t size_cmp = 0;

    uint32_t left_col_pos = -1;
    if(left.type == COLUMN){
        uint32_t* left_value = (uint32_t*)sark_alloc(1, sizeof(uint32_t));
        memcpy(left_value, left.value, sizeof(uint32_t));
        left_col_pos = get_byte_pos(*left_value);

         Column col = table->cols[*left_value];
         size_cmp = col.size;
    }

    uint32_t right_col_pos = -1;
    if(right.type == COLUMN){
        uint32_t* right_value = (uint32_t*)sark_alloc(1, sizeof(uint32_t));
        memcpy(right_value, right.value, sizeof(uint32_t));
        right_col_pos = get_byte_pos(*right_value);

        Column col = table->cols[*right_value];
        if(col.size > size_cmp){
            size_cmp = col.size;
        }
    }

    log_info("size_cmp is %d", size_cmp);

    */

    //todo allow for comparison of 2 literals!

    for(uint32_t row = 0; row < rows_in_this_core; row++, addr += row_size_words){

        uchar* values = addr;

        /*

        uchar* l = (left.type == COLUMN)  ? &values[left_col_pos]  : left.value;
        uchar* r = (right.type == COLUMN) ? &values[right_col_pos] : right.value;

        log_info("l -> %s", l);
        log_info("r -> %s", r);

        bool b;
        switch(condition.op){
            case EQ:;    b =  arr_equals(l, r, size_cmp); break;
            case NE:;    b = !arr_equals(l, r, size_cmp); break;

            //case GT:;       b = (*v  >  condition.value); break;
            //case GE:;       b = (*v  >= condition.value); break;
            //case LS:;       b = (*v  <  condition.value); break;
            //case LE:;       b = (*v  <= condition.value); break;
            case BETWEEN:;
            case LIKE:;
            case IN:;
            default:; b = true;                           break;
        }

        log_info("b is %s", b ? "true" : "false");

        if(b){
        */

        if(sel->col_names[0][0] == 0){ //wildcard

            uint p = 0;

            for(uint8_t col_index = 0; col_index < n_cols; col_index++){
                sdp_msg_t* msg = send_response_msg(sel, row, col_index, p, values);
                p += table->cols[col_index].size;
                //sark_msg_free(msg);
            }
         }
         else{
            for(uint8_t i = 0; i < MAX_NUMBER_OF_COLS; i++){
                if(sel->col_names[i][0] == 0){
                    break;
                }

                uint32_t col_index = get_col_index(sel->col_names[i]);

                if(col_index == -1){
                    continue;
                }

                uint32_t p = get_byte_pos(col_index);

                sdp_msg_t* msg = send_response_msg(sel, row, col_index, p, values);
            }
         }
    }
}
#endif