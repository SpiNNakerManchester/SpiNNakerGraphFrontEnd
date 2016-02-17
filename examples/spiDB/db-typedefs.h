#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

//if DB_HASH_TABLE is defined, the hash version is used.
//Naive version otherwise
#define DB_TYPE_KEY_VALUE_STORE
#define DB_SUBTYPE_HASH_TABLE

#define DB_TYPE_RELATIONAL

#define CHIP_X_SIZE                 2
#define CHIP_Y_SIZE                 2
#define CORE_SIZE                   16

#define ROOT_CORE                   1
#define FIRST_LEAF                  5
#define LAST_LEAF                   16
#define NUMBER_OF_LEAVES            (LAST_LEAF - FIRST_LEAF)

#define DEFAULT_NUMBER_OF_TABLES    16
#define MAX_NUMBER_OF_COLS          16

#define CORE_DATABASE_SIZE_WORDS    (120000000 >> 2) / CORE_SIZE

#define DEFAULT_TABLE_SIZE_WORDS    1024 //todo careful with overflow

#define try(cond) do { if (!cond) return false; } while (0)

typedef enum var_type  { UINT32, STRING } var_type;
typedef enum regions_e { SYSTEM_REGION, DB_DATA_REGION} regions_e;
typedef uint32_t id_t;

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

uint32_t to_info_single(var_type type, size_t size){
    return  ((type) << 12) | size;
}

uint32_t to_info(var_type k_type, size_t k_size,
                 var_type v_type, size_t v_size){
    return (to_info_single(k_type,k_size) << 16) | to_info_single(v_type,v_size);
}

var_type k_type_from_info(uint32_t info){
    return (info & 0xF0000000) >> 28;
}

size_t k_size_from_info(uint32_t info){
    return (info & 0x0FFF0000) >> 16;
}

var_type v_type_from_info(uint32_t info){
    return (info & 0x0000F000) >> 12;
}

size_t v_size_from_info(uint32_t info){
    return (info & 0x00000FFF);
}

bool arr_equals(uchar* a, uchar* b, uint32_t n){
    try(n > 0);

    for(uint32_t i = 0; i < n; i++){
        if(a[i] != b[i]){
            return false;
        }
    }
    return true;
}

typedef struct spiDBQueryHeader {
    spiDBcommand cmd;
    uint32_t     id;
} spiDBQueryHeader;

typedef struct pingQuery{
    spiDBcommand    cmd;
    uint32_t        id;
} pingQuery;

#ifdef DB_TYPE_RELATIONAL
    typedef struct Column {
        uchar    name[16];
        var_type type;
        size_t   size;
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
        uint32_t     id;

        Table table;
    } createTableQuery;

    typedef struct Entry{
        uint32_t row_id;
        uchar    col_name[16];
        size_t   size;
        uchar    value[256];
    } Entry;

    typedef struct insertEntryQuery { //INSERT INTO
        spiDBcommand cmd;
        uint32_t     id;

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
        COLUMN,
        LITERAL
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

    typedef struct Where {
        Condition  condition;
    } Where;

    typedef struct selectResponse {
        spiDBcommand cmd;
        uint32_t     id;

        Table*       table;
        address_t    addr;
    } selectResponse;

    typedef struct selectQuery {
        spiDBcommand cmd;
        uint32_t     id;

        uchar        table_name[16];
        uchar        col_names[MAX_NUMBER_OF_COLS][16]; //names == 0 means *

        //Where        where;
    } selectQuery;

#endif
#ifdef DB_TYPE_KEY_VALUE_STORE
    typedef struct putQuery{
        spiDBcommand    cmd;
        uint32_t        id;

        uint32_t        info;
        uchar           k_v[256];
    } putQuery;

    typedef struct pullQuery{
        spiDBcommand    cmd;
        uint32_t        id;

        uint32_t        info;
        uchar           k[256];
    } pullQuery;

    typedef struct pullReply{
        spiDBcommand    cmd;
        uint32_t        id;

        var_type        v_type;
        size_t          v_size;
        uchar           v[256];
    } pullReply;

    typedef struct value_entry {
        var_type type;
        size_t size;
        uchar* data;
    } value_entry;
#endif

typedef struct Response{
    uint32_t      id;
    spiDBcommand  cmd;

    bool          success;
    uchar         x;
    uchar         y;
    uchar         p;

    Entry         entry;
} Response;

uint32_t get_byte_pos(Table* table, uint32_t col_index){
    uint32_t pos = 0;

    if(col_index >= table->n_cols){
        return -1;
    }

    for(uint i = 0; i < col_index; i++){
        pos += table->cols[i].size;
    }

    return pos;
}

uint32_t get_col_index(Table* table, uchar col_name[16]){

    for(uint i = 0; i < table->n_cols; i++){
        if(strcmp(table->cols[i].name, col_name) == 0){
            return i;
        }
    }

    return -1;
}

uint32_t getTableIndex(Table* tables, uchar* name){
    for(uint i = 0; i < DEFAULT_NUMBER_OF_TABLES; i++){
        if(strcmp(tables[i].name, name) == 0){
            return i;
        }
    }
    return -1;
}

Table* getTable(Table* tables, uchar* name){
    uint32_t i = getTableIndex(tables, name);
    return i == -1 ? NULL : &tables[i];
}

bool in(uint* arr, size_t s, uint v){
    for(uint i = 0; i < s; i++){
        if(arr[i] == v){
            return true;
        }
    }
    return false;
}

void printEntry(Entry* e){
    log_info("####### Entry #######");
    log_info("row_id: %d", e->row_id);
    log_info("col_name: %s", e->col_name);
    log_info("size: %d", e->size);
    log_info("value: %s", e->value);
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
    for(uint i = 0; i < DEFAULT_NUMBER_OF_TABLES; i++){
        print_table(&tables[i]);
    }
}
#endif