#ifndef __SCAN_H__
#define __SCAN_H__

#include "../db-typedefs.h"
#include "../memory_utils.h"
#include <debug.h>

extern uchar chipx, chipy, core;
extern uchar branch;
extern uint32_t myId;
extern uint32_t rows_in_this_core;

sdp_msg_t* direct_to_branch(Table* table, selectQuery* sel, address_t addr){
    sdp_msg_t* msg = create_internal_sdp_header(branch);

    selectResponse* r = (selectResponse*)&msg->cmd_rc;
    r->cmd   = SELECT_RESPONSE;
    r->id    = sel->id;
    r->table = table;
    r->addr  = addr;

    log_info("Directing to branch %d value %s", branch, addr);

    msg->length = sizeof(sdp_hdr_t) + sizeof(selectResponse);

    while(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Retry sending selectResponse with addr=%08x to %d",
                   addr, branch);
        sark_delay_us(2);
    }

    log_info("Sending %08x to branch %d", addr, branch);

    return msg;
}

sdp_msg_t* send_response_msg(Table* table,
                             uint32_t sel_id,
                             uint32_t col_index,
                             uint32_t p,
                             uchar* values){

    sdp_msg_t* msg = create_sdp_header_to_host();

    Response* r = (Response*)&msg->cmd_rc;
    r->id  = sel_id;
    r->cmd = SELECT;
    r->success = true;
    r->x = chipx;
    r->y = chipy;
    r->p = core;

    Entry* e = &(r->entry);

    e->row_id = myId << 24 | (uint32_t)values;
    sark_word_cpy(e->col_name, table->cols[col_index].name, 16);
    e->size   = strlen(&values[p]); //todo how about non-Strings??
    sark_word_cpy(e->value, &values[p], e->size);

    log_info("Sending to host (%s,%s)", e->col_name, e->value);
                                  //4 + 16 + 4
    msg->length = sizeof(sdp_hdr_t) + 12 + 24 + e->size;

    if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
        log_error("Failed to send Response to host");
    }

    return msg;
}

void breakInBlocks(selectResponse* selResp){
    Table* table = selResp->table;
    uint32_t sel_id = selResp->id;
    address_t addr = selResp->addr;

    //if(sel->col_names[0][0] == 0){ //wildcard
    uint p = 0;

    size_t row_size_words = (table->row_size + 3) >> 2;
    size_t n_cols         = table->n_cols;

    for(uint8_t col_index = 0; col_index < n_cols; col_index++){
        sdp_msg_t* msg = send_response_msg(table,
                                           sel_id,
                                           col_index,
                                           p,
                                           (uchar*)addr);
        p += table->cols[col_index].size;

        sark_delay_us(2);
        //sark_msg_free(msg);
    }
     //}
     /*
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
     */
}

void scan_ids(Table* table,
              address_t addr,
              selectQuery* sel,
              uint32_t rows_in_this_core){

    if(!table){
        log_error("Unable to scan NULL table");
        return;
    }

    size_t row_size_words = (table->row_size + 3) >> 2;
    size_t n_cols         = table->n_cols;

    Condition condition = sel->condition;

    Operand  left  = condition.left;
    Operand  right = condition.right;

    uint32_t l_wordpos = 0;
    uint32_t r_wordpos = 0;

    uint32_t cmp_size;

    if(left.type == COLUMN){
        uint32_t col_index = get_col_index(table, left.value); //l represents the column name
        l_wordpos = get_byte_pos(table, col_index);

        cmp_size = table->cols[col_index].size;
    }

    if(right.type == COLUMN){
        uint32_t col_index = get_col_index(table, right.value); //r represents the column name
        r_wordpos = get_byte_pos(table, col_index);

        uint32_t r_cmp_size = table->cols[col_index].size;
        if(r_cmp_size > cmp_size){
            cmp_size = r_cmp_size;
        }
    }

    if(l_wordpos == -1 || r_wordpos == -1 || cmp_size <= 0){
        return;
    }

    l_wordpos >>= 2;
    r_wordpos >>= 2;

    //todo 2 literals cmp size???

    for(uint32_t row = 0; row < rows_in_this_core; row++, addr += row_size_words){

        uchar* l = (left.type == COLUMN)  ? addr+(l_wordpos) : left.value;
        uchar* r = (right.type == COLUMN) ? addr+(r_wordpos) : right.value;

        bool b = false;
        switch(condition.op){
            case EQ:;    b =  arr_equals(l, r, cmp_size); break;
            case NE:;    b = !arr_equals(l, r, cmp_size); break;
            case GT:;    b = *l  >  *r;                   break;
            case GE:;    b = *l  >= *r;                   break;
            case LT:;    b = *l  <  *r;                   break;
            case LE:;    b = *l  <= *r;                   break;
            case BETWEEN:;
            case LIKE:;
            case IN:;
            default:; b = true;                           break;
        }

        log_info("%s %s %s ? %s", l, getOperatorName(condition.op), r,
                 b ? "True" : "False");

        if(b){
            direct_to_branch(table, sel, addr);
            sark_delay_us(1);
        }
    }
}
#endif