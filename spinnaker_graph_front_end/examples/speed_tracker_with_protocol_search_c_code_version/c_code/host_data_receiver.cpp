#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <list>
#include <set>
#include "UDPConnection.h"
#include "SDPMessage.h"

using namespace std;

// constants for messages
static const int SDP_PACKET_START_SENDING_COMMAND_ID = 100;
static const int SDP_PACKET_START_MISSING_SEQ_COMMAND_ID = 1000;
static const int SDP_PACKET_MISSING_SEQ_COMMAND_ID = 1001;
static const int SDP_PACKET_PORT = 2;
static const int SDP_RETRANSMISSION_HEADER_SIZE = 2;
static const int SDP_PACKET_START_SENDING_COMMAND_MESSAGE_SIZE = 1;

// time out constants
static const int TIMEOUT_PER_RECEIVE_IN_SECONDS = 1;
static const float TIMEOUT_PER_SENDING_IN_SECONDS = 0.01;

// consts for data and converting between words and bytes
static const int SDRAM_READING_SIZE_IN_BYTES_CONVERTER = 1024 * 1024;
static const int DATA_PER_FULL_PACKET = 68;
static const int DATA_PER_FULL_PACKET_WITH_SEQUENCE_NUM =
    DATA_PER_FULL_PACKET - 1;
static const int WORD_TO_BYTE_CONVERTER = 4;


void send_initial_command(
        UDPConnection sender,  int placement_x, int placement_y,
        int placement_p, int port_connection){

    // send first message
    unsigned char start_message_data[SDPMessage::MAX_PACKET_SIZE_DATA];

    // add data
    start_message_data[0] = SDP_PACKET_START_SENDING_COMMAND_ID;

    // build SDP message
    SDPMessage message = SDPMessage(
        placement_x, placement_y, placement_p, port_connection,
        SDPMessage::REPLY_NOT_EXPECTED, start_message_data,
        SDP_PACKET_START_SENDING_COMMAND_MESSAGE_SIZE);

    sender.send_data(message.convert_to_byte_array(),
                     message.length_in_bytes());
}


int main(int argc, char *argv[])
{
    // constants for arguments
    static const int N_ARGS = 7;
    static const int IP_ADDRESS_SIZE = 24;
    static const int FILE_PATH_SIZE = 1024;

    // enum for arg positions
    enum arg_placements{
        PLACEMENT_X_POSITION = 0,
        PLACEMENT_Y_POSITION = 1,
        PLACEMENT_P_POSITION = 2,
        PORT_NUMBER_POSITION = 3,
        HOSTNAME_POSITION = 4,
        FILE_PATH_POSITION = 5};

    // variables
    int placement_x = 0;
    int placement_y = 0;
    int placement_p = 0;
    int port_connection = 0;
    char *hostname = NULL;
    char *file_path = NULL;
    int max_seq_num = 0;
    FILE * stored_data;
    char * output = NULL;

    // state variables for reception
    bool finished = false;
    bool first = false;
    int seq_num = 1;
    set<int> received_seq_nums;


    // placement x, placement y, placement p, port, host, data loc
    if(argc != N_ARGS){
        printf("not the correct number of parameters");
        return 1;
    }

    // get arguments
    placement_x = atoi(argv[PLACEMENT_X_POSITION]);
    placement_y = atoi(argv[PLACEMENT_Y_POSITION]);
    placement_p = atoi(argv[PLACEMENT_P_POSITION]);
    port_connection = atoi(argv[PORT_NUMBER_POSITION]);
    hostname = argv[HOSTNAME_POSITION];
    file_path = argv[FILE_PATH_POSITION];

    // create data store.
    stored_data = fopen(file_path, "w");

    // create connection for sending messages to core
    UDPConnection sender = UDPConnection(NULL, NULL, NULL, hostname);

    // create connection for receiving messages from core
    UDPConnection receiver = UDPConnection(
        port_connection, "localhost", NULL, NULL);

    // send the initial command to start data transmission
    send_initial_command(
        sender, placement_x, placement_y, placement_p, port_connection);












    // work

    return 0;
}