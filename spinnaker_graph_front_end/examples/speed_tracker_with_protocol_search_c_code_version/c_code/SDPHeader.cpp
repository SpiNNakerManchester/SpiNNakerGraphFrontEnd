#include "SDPHeader.h"

SDPHeader::SDPHeader(
        int destination_chip_x, int destination_chip_y,
        int destination_cpu, int destination_port,
        int flags, int tag, int source_port, int source_cpu,
        int source_chip_x, int source_chip_y){
    this->destination_chip_x = destination_chip_x;
    this->destination_chip_y = destination_chip_y;
    this->destination_chip_p = destination_cpu;
    this->destination_port = destination_port;
    this->flags = flags;
    this->tag = tag;
    this->source_port = source_port;
    this->source_cpu = source_cpu;
    this->source_chip_x = source_chip_x;
    this->source_chip_y = source_chip_y;
}


char * SDPMessage::convert_to_byte_array(){
    unsigned char * message_data;
    strcat(message_data, this->destination_chip_x);
    strcat(message_data, this->data);
    return message_data;
}

int SDPMessage::length_in_bytes(){
    return this->length + this->header.length();
}
