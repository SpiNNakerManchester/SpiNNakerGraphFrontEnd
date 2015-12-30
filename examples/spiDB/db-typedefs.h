#ifndef __DB_TYPEDEFS_H__
#define __DB_TYPEDEFS_H__

//if DB_HASH_TABLE is defined, the hash version is used.
//Naive version otherwise
//#define DB_HASH_TABLE

//TODO these should not be hardcoded
#define CHIP_X_SIZE 2
#define CHIP_Y_SIZE 2
#define CORE_SIZE   16

#define ROOT_CORE       1
#define FIRST_SLAVE     1
#define LAST_SLAVE      CORE_SIZE
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

    PUT_REPLY_ACK, //still needs implementing...
    PULL_REPLY_ACK
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
    size_t   size;
    var_type type;
} Column;

typedef struct Table {
    size_t      n_cols;
    size_t      row_size;
    Column      cols[4];
} Table;

typedef struct createTableQuery {
    spiDBcommand cmd;
    uint32_t     id;

    Table table;
} createTableQuery;


typedef struct insertQuery { //insert into
    spiDBcommand cmd;
    uint32_t     id;

    uchar        values[256];
} insertQuery;

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

typedef struct selectQuery {
    spiDBcommand cmd;
    uint32_t     id;

    Where        where;
    //simply do for SELECT * for now
} selectQuery;

#endif