#ifdef DB_TYPE_RELATIONAL

    #ifndef __SCAN_H__
    #define __SCAN_H__

    #include "../db-typedefs.h"
    #include "../memory_utils.h"
    #include <debug.h>

    extern uchar chipx, chipy, core;
    extern uchar branch;
    extern id_t myId;

    extern uint32_t rows_in_this_core;

    sdp_msg_t* direct_to_branch(Table* table,
                                selectQuery* sel,
                                address_t addr,
                                uchar n_cols_to_select,
                                uchar* col_indices_to_select){

        sdp_msg_t* msg = create_internal_sdp_header(branch);

        selectResponse* r = (selectResponse*)&msg->cmd_rc;
        r->cmd   = SELECT_RESPONSE;
        r->id    = sel->id;
        r->table = table;
        r->addr  = addr;
        r->n_cols = n_cols_to_select;
        sark_mem_cpy(r->col_indices, col_indices_to_select,
                     n_cols_to_select * sizeof(uchar));

        msg->length = sizeof(sdp_hdr_t) + sizeof(selectResponse);

        while(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
            log_error("Retry sending selectResponse with addr=%08x to %d",
                       addr, branch);
            sark_delay_us(2);
        }

        log_info("Sending %08x to branch %d", addr, branch);

        return msg;
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

        uchar* col_indices_to_sel = (uchar*) sark_alloc(MAX_NUMBER_OF_COLS,
                                                        sizeof(uchar));

        size_t n_cols_sel = 0;

        for(; n_cols_sel < MAX_NUMBER_OF_COLS; n_cols_sel++){
            int col_i = get_col_index(table, sel->col_names[n_cols_sel]);

            if(col_i == -1){
                break;
            }

            col_indices_to_sel[n_cols_sel] = col_i;
        }

        Condition condition = sel->condition;

        //determines whether a WHERE clause has been specified
        bool where = !(condition.left.type == COLUMN
                       && *condition.left.value == 0);

        uint32_t row = 0;

        if(where){
            Operand  left  = condition.left;
            Operand  right = condition.right;

            int l_wordpos = 0;
            int r_wordpos = 0;

            size_t cmp_size;

            if(left.type == COLUMN){
                uint32_t col_index = get_col_index(table, left.value);
                l_wordpos = get_byte_pos(table, col_index);

                cmp_size = table->cols[col_index].size;
            }

            if(right.type == COLUMN){
                uint32_t col_index = get_col_index(table, right.value);
                r_wordpos = get_byte_pos(table, col_index);

                uint32_t r_cmp_size = table->cols[col_index].size;
                if(r_cmp_size > cmp_size){
                    cmp_size = r_cmp_size;
                }
            }

            if(l_wordpos == -1 || r_wordpos == -1 || cmp_size <= 0){
                return;
            }

            if(left.type == LITERAL_UINT32 || right.type == LITERAL_UINT32){
                cmp_size = sizeof(uint32_t);
            }

            l_wordpos >>= 2;
            r_wordpos >>= 2;

            for(;row < rows_in_this_core; row++, addr += row_size_words){

                uchar* l = (left.type == COLUMN)  ?
                            (uchar*)(addr+l_wordpos) : left.value;
                uchar* r = (right.type == COLUMN) ?
                            (uchar*)(addr+r_wordpos) : right.value;

                bool b;
                switch(condition.op){
                    case EQ:;    b =  arr_equals(l, r, cmp_size);  break;
                    case NE:;    b = !arr_equals(l, r, cmp_size);  break;
                    case GT:;    b = *l   >  *r;                   break;
                    case GE:;    b = *l   >= *r;                   break;
                    case LT:;    b = *l   <  *r;                   break;
                    case LE:;    b = *l   <= *r;                   break;
                    case BETWEEN:; //todo
                    case LIKE:;
                    case IN:;
                    default:;    b = true;                         break;
                }

                if(b){
                    direct_to_branch(table, sel, addr,
                                     n_cols_sel, col_indices_to_sel);
                    sark_delay_us(1);
                }
            }
        }
        else{
            for(;row < rows_in_this_core; row++, addr += row_size_words){
                direct_to_branch(table, sel, addr,
                                 n_cols_sel, col_indices_to_sel);
                sark_delay_us(1);
            }
        }

        sark_free(col_indices_to_sel);
    }
    #endif
#endif