#ifndef __DB_TYPEDEFS_H__
    #define __DB_TYPEDEFS_H__

    ///////////////////////////////////////////////////////////////////////////
    //// These values can be set/unset according to the desired type of DB ////
    ///////////////////////////////////////////////////////////////////////////
    #define DB_TYPE_KEY_VALUE_STORE
        #ifdef DB_TYPE_KEY_VALUE_STORE
            #define DB_SUBTYPE_HASH_TABLE
            #ifdef DB_SUBTYPE_HASH_TABLE
                //#define HASH_FUNCTION_DFJB
                //#define HASH_FUNCTION_XOR
                #define HASH_FUNCTION_JENKINGS
            #endif
    #endif

    #define DB_TYPE_RELATIONAL
    ///////////////////////////////////////////////////////////////////////////

    #define CHIP_X_SIZE                 2
    #define CHIP_Y_SIZE                 2
    #define CORE_SIZE                   17

    #define ROOT_CORE                   1
    #define FIRST_LEAF                  5
    #define LAST_LEAF                   16
    #define NUMBER_OF_LEAVES            (LAST_LEAF - FIRST_LEAF)

    #define DEFAULT_NUMBER_OF_TABLES    16
    #define MAX_NUMBER_OF_COLS          6
    #define MAX_COL_NAME_SIZE           16

    #define CORE_DATABASE_SIZE_WORDS    (120000000 >> 2) / CORE_SIZE
    #define ROOT_SDRAM_SIZE_BYTES       2097152

    #define DEFAULT_TABLE_SIZE_WORDS    1024 //todo careful with overflow

    #define MULTIPLE_OF_4(n) (((n+3)/4)*4)
    #define try(cond) do { if (!cond) return false; } while (0)

    typedef enum var_type  { UINT32=0, STRING } var_type;
    typedef enum regions_e { SYSTEM_REGION=0, DB_DATA_REGION} regions_e;
    typedef uint32_t id_t;
    typedef uint32_t info_t;

    uchar chipx, chipy, core;

    typedef enum spiDBcommand {
        PUT = 0,
        PULL,

        CLEAR,

        PUT_REPLY,
        PULL_REPLY,

        CREATE_TABLE,
        INSERT_INTO,
        SELECT,
        SELECT_RESPONSE,

        PING
    } spiDBcommand;

    typedef struct spiDBQueryHeader {
        spiDBcommand cmd;
        id_t         id;
    } spiDBQueryHeader;

    typedef struct Response_hdr{
        id_t          id;
        spiDBcommand  cmd;

        bool          success;
        uchar         x;
        uchar         y;
        uchar         p;

        uchar         padding[3];
    } Response_hdr;

    typedef struct Response{
        id_t          id;
        spiDBcommand  cmd;

        bool          success;
        uchar         x;
        uchar         y;
        uchar         p;

        uchar         padding[3]; //used to word-align the data

        uchar         data[256];
    } Response;

    void printResponse(Response* r){
        log_info("###### RESPONSE #######");
        log_info("id : %d", r->id);
        log_info("cmd: %d", r->cmd);
        log_info("success: %d", r->success);
        log_info("x: %d, y: %d, p: %d", r->x, r->y, r->p);
        log_info("data %s", r->data);
        log_info("");
    }

    #ifdef DB_TYPE_KEY_VALUE_STORE
        info_t to_info_single(var_type type, size_t size){
            return  ((type) << 12) | size;
        }

        info_t to_info(var_type k_type, size_t k_size,
                         var_type v_type, size_t v_size){
            return (to_info_single(k_type,k_size) << 16)
                    | to_info_single(v_type,v_size);
        }

        var_type k_type_from_info(info_t info){
            return (info & 0xF0000000) >> 28;
        }

        size_t k_size_from_info(info_t info){
            return (info & 0x0FFF0000) >> 16;
        }

        var_type v_type_from_info(info_t info){
            return (info & 0x0000F000) >> 12;
        }

        size_t v_size_from_info(info_t info){
            return (info & 0x00000FFF);
        }
    #endif


    #ifdef DB_TYPE_RELATIONAL
        typedef struct Column {
            uchar       name[16];
            var_type    type;
            size_t      size;
        } Column;

        typedef struct Table {
            uchar       name[16];
            size_t      n_cols;
            size_t      row_size;
            size_t      current_n_rows;
            Column      cols[4];
        } Table;

        typedef struct createTableQuery {
            spiDBcommand cmd;
            id_t         id;

            Table        table;
        } createTableQuery;

        typedef struct Entry_hdr{
            id_t        row_id;
            uchar       col_name[16];
            size_t      size;
            var_type    type;

            uchar       pad[3];
        } Entry_hdr;

        typedef struct Entry{
            id_t        row_id;
            uchar       col_name[16];
            size_t      size;
            var_type    type;

            uchar       pad[3]; //padding for the value

            uchar       value[256];
        } Entry;

        typedef struct insertEntryQuery { //INSERT INTO
            spiDBcommand cmd;
            id_t         id;

            uchar        table_name[16];
            Entry        e;
        } insertEntryQuery;

        /*
        =	Equal
        <>	Not equal. Note: In some versions of SQL this operator may be written as !=
        >	Greater than
        >=	Greater than or equal
        <	Less than
        <=	Less than or equal
        BETWEEN	Between an inclusive range
        LIKE	Search for a pattern
        IN	To specify multiple possible values for a column
        */
        typedef enum {
            EQ = 0,
            NE,
            GT,
            GE,
            LT,
            LE,
            BETWEEN,
            LIKE,
            IN
        } Operator;

        typedef enum {
            LITERAL_UINT32 = 0,
            LITERAL_STRING,
            COLUMN
        } OperandType;

        typedef struct Operand {
            OperandType type;
            uchar       value[64];
        } Operand;

        typedef struct Condition {
            Operand     left;
            Operator    op;
            Operand     right;
        } Condition;

        typedef struct selectResponse {
            spiDBcommand cmd;
            id_t         id;

            Table*       table;
            address_t    addr;

            uchar        n_cols;
            uchar        col_indices[MAX_NUMBER_OF_COLS];
        } selectResponse;

        typedef struct selectQuery {
            spiDBcommand cmd;
            id_t         id;

            uchar        table_name[16];
            uchar        col_names[MAX_NUMBER_OF_COLS][16];//names == 0 means *

            Condition    condition;
        } selectQuery;

        int get_byte_pos(Table* table, int col_index){
            uint32_t pos = 0;

            if(col_index == -1 || col_index >= table->n_cols){
                return -1;
            }

            for(uint i = 0; i < col_index; i++){
                pos += table->cols[i].size;
            }

            return pos;
        }

        int get_col_index(Table* table, uchar col_name[16]){

            for(uint i = 0; i < table->n_cols; i++){
                if(strcmp(table->cols[i].name, col_name) == 0){
                    return i;
                }
            }

            return -1;
        }

        int getTableIndex(Table* tables, uchar* name){
            for(uint i = 0; i < DEFAULT_NUMBER_OF_TABLES; i++){
                if(strcmp(tables[i].name, name) == 0){
                    return i;
                }
            }
            return -1;
        }

        Table* getTable(Table* tables, uchar* name){
            int i = getTableIndex(tables, name);
            return i == -1 ? NULL : &tables[i];
        }

        char* getOperatorName(Operator o){
            switch(o){
              case EQ:      return "=";
              case NE:      return "!=";
              case GT:      return ">";
              case GE:      return ">=";
              case LT:      return "<";
              case LE:      return "<=";
              case BETWEEN: return "BETWEEN";
              case LIKE:    return "LIKE";
              case IN:      return "IN";
              default:      return "?";
            }
        }

        void printEntry(Entry* e){
            log_info("####### Entry #######");
            if(!e){
                log_info(" |- NULL -|");
                return;
            }
            log_info("row_id: %d", e->row_id);
            log_info("col_name: %s", e->col_name);
            log_info("size: %d", e->size);
            log_info("type: %s", e->type == UINT32 ? "UINT32" : "STRING");
            if(e->type == UINT32){
                log_info("value: %d", *e->value);
            }
            else{
                log_info("value: %s", e->value);
            }

            log_info("########################");
        }

        void print_table(Table* t){
            log_info("####### TABLE #######");
            log_info("name %s", t->name);
            log_info("n_cols %d", t->n_cols);
            log_info("row_size %d", t->row_size);
            log_info("current_n_rows %d", t->current_n_rows);

            for(uint i = 0; i < t->n_cols; i++){
                log_info("  cols[%d] = name: %s, type: %d, size: %d",
                            i, t->cols[i].name, t->cols[i].type, t->cols[i].size);
            }
            log_info("#####################");
        }

        void print_tables(Table* tables){
            log_info("---- Tables at %08x", tables);
            for(uint i = 0; i < DEFAULT_NUMBER_OF_TABLES; i++){
                print_table(&tables[i]);
            }
        }

        void print_SELECT(selectQuery* selQ){
            log_info("############################################");
            io_printf(IO_BUF, "SELECT ");

            if(selQ->col_names[0][0] == 0){
                io_printf(IO_BUF, "*");
            }
            else{
                for(uint i = 0; i < MAX_NUMBER_OF_COLS; i++){
                    if(selQ->col_names[i][0] == NULL){
                        break;
                    }
                    io_printf(IO_BUF, "%s, ", selQ->col_names[i]);
                }
            }

            io_printf(IO_BUF, " FROM %s", selQ->table_name);

            if(selQ->condition.left.type == COLUMN && *selQ->condition.left.value == 0){
                //ie no WHERE clause
                io_printf(IO_BUF, ";\n");
                return;
            }

            io_printf(IO_BUF, " WHERE (%s) %s %s (%s) %s;\n",
                      selQ->condition.left.type == COLUMN ? "COLUMN" : "LITERAL",
                      selQ->condition.left.value,
                      getOperatorName(selQ->condition.op),
                      selQ->condition.right.type == COLUMN ? "COLUMN" : "LITERAL",
                      selQ->condition.right.value);
        }
    #endif
    #ifdef DB_TYPE_KEY_VALUE_STORE
        typedef struct putPullQuery{
            spiDBcommand    cmd;
            id_t            id;

            info_t          info;
            uchar           data[256];
        } putPullQuery;

        typedef struct putQuery{
            spiDBcommand    cmd;
            id_t            id;

            info_t          info;
            uchar           k_v[256];
        } putQuery;

        typedef struct pullQuery{
            spiDBcommand    cmd;
            id_t            id;

            info_t          info;
            uchar           k[256];
        } pullQuery;

        typedef struct pullValue{
            var_type type;
            size_t   size;

            uchar    pad[3];//padding for the data

            uchar    data[256];
        } pullValue;

        typedef struct pullValueResponse_hdr{
            spiDBcommand    cmd;
            id_t            id;

            uchar           pad[3];
        } pullValueResponse_hdr;

        typedef struct pullValueResponse{
            spiDBcommand    cmd;
            id_t            id;

            uchar           pad[3];

            pullValue       v;
        } pullValueResponse;

        void printPullValue(pullValue* p){
            log_info("(type: %s, size: %d, data: %s)",
                 p->type == UINT32 ? "UINT32" : "STRING",
                 p->size, p->data);
        }
    #endif
#endif