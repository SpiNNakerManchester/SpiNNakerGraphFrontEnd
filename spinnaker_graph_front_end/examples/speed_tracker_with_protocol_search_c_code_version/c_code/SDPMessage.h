#include "SDPHeader.h"

class SDPMessage{

    public:
        SDPMessage(int destination_chip_x, int destination_chip_y,
                   int destination_chip_p, int destination_port, int flags,
                   unsigned char * data, int length);
        ~SDPMessage();

        unsigned char* convert_to_byte_array();
        int length_in_bytes();
        static const int MAX_PACKET_SIZE = 300;
        static const int MAX_PACKET_SIZE_DATA = 292;
        static const int REPLY_NOT_EXPECTED = 0x07;

    private:
        char * data;
        SDPHeader header;
        int data_length;


};