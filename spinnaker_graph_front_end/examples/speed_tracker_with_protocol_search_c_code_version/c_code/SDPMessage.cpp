#include "SDPMessage.h"
#include "SDPHeader.h"

SDPMessage::SDPMessage(
        int destination_chip_x, int destination_chip_y, int destination_chip_p,
        int destination_port, int flags, unsigned char * data,
        int data_length){

    this->data = data;
    this->data_length = data_length;
    this->header = SDPHeader(destination_chip_x, destination_chip_y,
                             destination_port, flags);

}

char * SDPMessage::convert_to_byte_array(){
    unsigned char * message_data;
    strcat(message_data, this->header.convert_to_byte_array());
    strcat(message_data, this->data);
    return message_data;
}

int SDPMessage::length_in_bytes(){
    return this->length + this->header.length();
}

