__author__ = 'gmtuca'

import struct
from result import Entry

def translate(table,response_str):

    #keep track of table

    response = struct.unpack_from("III", response_str)

    (row_id, col_index, size) = response
    value = response_str[12:]

    #if select

    return Entry(row_id,table.cols[col_index].name,value,-1)


    """
    typedef struct Entry{
        uint32_t row_id;
        uint32_t col_index;
        size_t   size;
        uchar    value[256];
    } Entry;
    """



    return ""