#ifndef __SCAN_H__
#define __SCAN_H__

#include "../db-typedefs.h"
#include "../memory_utils.h"
#include <debug.h>

extern Table* table;
extern uchar chipx;
extern uchar chipy;
extern uchar core;

void scan_ids(address_t addr, selectQuery* sel){

    if(!table){
        return;
    }

    size_t row_size_words = (table->row_size + 3) >> 2;
    size_t current_n_rows = table->current_n_rows; //todo only like this when table is on a single core
    size_t n_cols         = table->n_cols;

    print_table(table);

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

    for(uint32_t row_id = 0; row_id < current_n_rows; row_id++, addr += row_size_words){

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

            for(uint8_t i = 0; i < n_cols; i++){
                /*
                typedef struct Entry{
                    uint32_t row_id;
                    uchar    col_name[16];
                    size_t   size;
                    uchar    value[256];
                } Entry;
                */

                //todo recycle msg?
                sdp_msg_t* msg = create_sdp_header_to_host();

                Response* response = (Response*)&msg->cmd_rc;
                response->id  = sel->id;
                response->cmd = sel->cmd;
                response->success = true;
                response->x = chipx;
                response->y = chipy;
                response->p = core;

                Entry* e = &response->entry;
                //sizeof(Response); //BUT SIZE OF RESPONSE IS 12 BECAUSE OF ALIGNING

                e->row_id = row_id;
                memcpy(e->col_name, table->cols[i].name, 16);
                e->size   = strlen(&values[p]); //todo how about non-Strings??
                memcpy(e->value, &values[p], e->size);

                log_info("(%d) %s -> %s", e->row_id, e->col_name, e->value);

                                                                //4 + 16 + 4
                msg->length = sizeof(sdp_hdr_t) + 12 + 24 + e->size;

                spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                p += table->cols[i].size;
            }
         }
        /* } */


/*
    typedef struct Entry{
        uint32_t row_id;
        uint32_t col_index;
        uchar    value[256];
    } Entry;
*/


        /*
        typedef enum {
            EQ = 0,
            GT,
            GE,
            LS,
            LE
        } Comparison;

        typedef struct Condition {
            Comparison  comparison;
            uint8_t     col_index;
            uint32_t    value;
        } Condition;

        typedef struct Where {
            Condition  condition;
        } Where;

        typedef struct selectQuery {
            spiDBcommand cmd;
            uint32_t     id;

            Where        where;
            //simply do for SELECT * for now
        } selectQuery;


        */

        /*
            size_t      n_cols;
            size_t      row_size;
            size_t      col_sizes[4];
        */


        /*
        addr++;


        var_type k_type  = k_type_from_info(curr_info);
        size_t   k_size  = k_size_from_info(curr_info);

        var_type v_type  = v_type_from_info(curr_info);
        size_t   v_size  = v_size_from_info(curr_info);

        size_t k_size_words = (k_size+3) >> 2;
        size_t v_size_words = (v_size+3) >> 2;

        uchar* k = (uchar*)addr;
        addr += k_size_words;

        uchar* v = (uchar*)addr;
        addr += v_size_words;
        */




    }
}
#endif