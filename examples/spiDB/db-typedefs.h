#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

//if DB_HASH_TABLE is defined, the hash version is used.
//Naive version otherwise

//#define DB_TYPE_KEY_VALUE_STORE
//#define DB_SUBTYPE_HASH_TABLE

#define DB_TYPE_RELATIONAL

//TODO these should not be hardcoded
#define CHIP_X_SIZE 2
#define CHIP_Y_SIZE 2
#define CORE_SIZE   16

#define ROOT_CORE           1
#define FIRST_LEAF          5
#define LAST_LEAF           16
#define NUMBER_OF_LEAVES    LAST_LEAF - FIRST_LEAF

                                          //words
#define CORE_DATABASE_SIZE_WORDS (120000000 >> 2) / CORE_SIZE

typedef enum { UINT32, STRING } var_type;

typedef enum regions_e {
    SYSTEM_REGION, DB_DATA_REGION
} regions_e;

#define try(cond) do { if (!cond) return false; } while (0)

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

typedef struct spiDBquery {
    spiDBcommand cmd;
    uint32_t     id;

    var_type k_type;
    size_t   k_size;

    //these are ignored in case of a PULL
    var_type v_type;
    size_t   v_size;

    uchar k_v[256];
} spiDBquery;

typedef struct value_entry {
    var_type type;
    size_t size;
    uchar* data;
} value_entry;

uint32_t to_info_single(var_type type, size_t size){
    return  ((type) << 12) | size;
}

uint32_t to_info(var_type k_type, size_t k_size, var_type v_type, size_t v_size){
    return (to_info_single(k_type,k_size) << 16) | to_info_single(v_type,v_size);
}

var_type k_type_from_info(uint32_t info){
    return (info & 0xF0000000) >> 28;
}

size_t k_size_from_info(uint32_t info){
    return (info & 0x0FFF0000) >> 16;
}

size_t v_type_from_info(uint32_t info){
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

//////////////////////////////////////////////////////////////////////////

typedef struct spiDBQueryHeader {
    spiDBcommand cmd;
    uint32_t     id;
} spiDBQueryHeader;

typedef struct Column {
    uchar    name[16];
    var_type type;
    size_t   size;
} Column;

typedef struct Table {
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

    //todo tablename?
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

#define MAX_NUMBER_OF_COLS 16

typedef struct selectResponse {
    spiDBcommand cmd;
    uint32_t     id;

    address_t addr;
} selectResponse;

typedef struct selectQuery {
    spiDBcommand cmd;
    uint32_t     id;

    //uchar      table_name;
    uchar        col_names[MAX_NUMBER_OF_COLS][16]; //If col names == 0, it means SELECT *

    //Where        where;??
    //simply do for SELECT * for now
} selectQuery;


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

typedef struct pingQuery{
    spiDBcommand    cmd;
    uint32_t        id;
} pingQuery;

typedef struct pullReply{
    spiDBcommand    cmd;
    uint32_t        id;

    var_type        v_type;
    size_t          v_size;
    uchar           v[256];
} pullReply;

#endif

extern Table* table;

typedef struct Response{
    uint32_t      id;
    spiDBcommand  cmd;

    bool          success;
    uchar         x;
    uchar         y;
    uchar         p;

    Entry         entry;
} Response;

//todo should be put in the table
uint32_t get_byte_pos(uint32_t col_index){
    uint32_t pos = 0;

    if(col_index >= table->n_cols){
        return -1;
    }

    for(uint32_t i = 0; i < col_index; i++){
        pos += table->cols[i].size;
    }

    return pos;
}

#include <debug.h>

uint32_t get_col_index(uchar col_name[16]){

    for(uint32_t i = 0; i < table->n_cols; i++){
        //log_info("cmp %s with %s", table->cols[i].name, col_name);

        if(strcmp(table->cols[i].name, col_name) == 0){
            //log_info("YES");
            return i;
        }
    }

    return -1;
}

////////////////////////////////////////////////////////////////////////



#endif