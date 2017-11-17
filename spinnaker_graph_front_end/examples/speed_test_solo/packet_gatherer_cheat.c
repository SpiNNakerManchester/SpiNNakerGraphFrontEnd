
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

//!###################### magic numbers
//! the number of DMA buffers to build
#define N_DMA_BUFFERS 2

//! flag size for saying ended
#define END_FLAG_SIZE 4

//! flag for saying stuff has ended
#define END_FLAG 0xFFFFFFFF

//! sdp port for packets.
#define SDP_PORT_FOR_SDP_PACKETS 2

//! items per SDP packet for sending
#define ITEMS_PER_DATA_PACKET 68

//! convert between words to bytes
#define WORD_TO_BYTE_MULTIPLIER 4

//!################## sdp flags
//! send data command id in SDP
#define SDP_COMMAND_FOR_SENDING_DATA 100

//! start missing sdp seq nums in SDP (this includes n SDP packets expected)
#define SDP_COMMAND_FOR_START_OF_MISSING_SDP_PACKETS 1000

//! other missing sdp seq nums in SDP
#define SDP_COMMAND_FOR_MORE_MISSING_SDP_PACKETS 1001

//! timeout for trying to end SDP packet
#define SDP_TIMEOUT 1000

//! extra length adjustment for the sdp header
#define LENGTH_OF_SDP_HEADER 8

//################### dma tags
//! dma complete tag for retransmission of data
#define DMA_TAG_READ_FOR_RETRANSMISSION 1

//! dma complete tag for original transmission, this isnt used yet, but needed
//! for full protocol
#define DMA_TAG_READ_FOR_TRANSMISSION 0

//! struct for a SDP message with pure data, no scp header
typedef struct sdp_msg_pure_data {	// SDP message (=292 bytes)
    struct sdp_msg *next;		// Next in free list
    uint16_t length;		// length
    uint16_t checksum;		// checksum (if used)

    // sdp_hdr_t
    uint8_t flags;	    	// SDP flag byte
    uint8_t tag;		      	// SDP IPtag
    uint8_t dest_port;		// SDP destination port/CPU
    uint8_t srce_port;		// SDP source port/CPU
    uint16_t dest_addr;		// SDP destination address
    uint16_t srce_addr;		// SDP source address

    // User data (272 bytes when no scp header)
    uint32_t data[ITEMS_PER_DATA_PACKET];

    uint32_t _PAD;		// Private padding
} sdp_msg_pure_data;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! transmission stuff
static uint32_t data[ITEMS_PER_DATA_PACKET];
static uint32_t position_in_store = 0;
static uint32_t total_position = 0;
static bool check = false;

//! retransmission stuff
static uint32_t use_seq;
static uint32_t missing_sdp_packets = 0;
static uint32_t final_seq_num = 0;
static uint32_t data_written = 0;
address_t missing_sdp_seq_num_sdram_address = NULL;

//! retransmission dma stuff
static uint32_t *dma_data[N_DMA_BUFFERS];
static uint32_t dma_pointer = 0;
static uint32_t position_for_retransmission = 0;

//! sdp message holder for transmissions
sdp_msg_pure_data my_msg;

//! state for how many bytes it needs to send, gives approx bandwidth if 
//! round number. 
static uint32_t bytes_to_write;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION, CONFIG
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, SDP = 0, DMA = 0
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum config_region_elements {
    MB, ADD_SEQ
} config_region_elements;


//! sends original data to host
void send_data(uint32_t * data_to_send, uint32_t size_in_bytes){
   //log_info("last element is %d", data[position_in_store - 1]);
   //log_info("first element is %d", data[0]);
   if(check){
      log_info("data being sent is %x", data_to_send[0]);
      check = false;
   }
   spin1_memcpy(&my_msg.data, (void *)data_to_send, size_in_bytes);
   my_msg.length = LENGTH_OF_SDP_HEADER + size_in_bytes;
   while(!spin1_send_sdp_msg (&my_msg, SDP_TIMEOUT)){
       log_error("cant send sdp packet");
   }
   //log_info("sent data");
   position_in_store = 0;
}

//! start the creation of data and firing off to host
void start_data(){
    uint top_value = (uint)(bytes_to_write / WORD_TO_BYTE_MULTIPLIER);
    log_info("top value is %d", top_value);
    data[0] = bytes_to_write;
    position_in_store = 1;
    bool needs_seq_num = false;
    uint32_t seq_num = 1;

    log_info("bytes to write is %d, top value is %d",
             bytes_to_write, top_value);

    //! iterate from 0 to top value emulating sdram reads
    for(uint count = 0; count < top_value; count++){
    
        // if first, put seq num in
        if(needs_seq_num && use_seq == 1){
            data[position_in_store] = seq_num;
            position_in_store +=1;
            seq_num +=1;
            needs_seq_num = false;
        }
        
        // store new value in data
        data[position_in_store] = count;
        position_in_store += 1;
        
        // if full send sdp packet
        if (position_in_store == ITEMS_PER_DATA_PACKET){
            //log_info("sending packet");
            send_data(data, position_in_store * WORD_TO_BYTE_MULTIPLIER);
            position_in_store = 0;
            needs_seq_num = true;
        }
    }

    log_info("sending final state");
    data[position_in_store] = END_FLAG;
    position_in_store +=1;
    send_data(data, position_in_store * WORD_TO_BYTE_MULTIPLIER);
}

//! write SDP seq nums to sdram that need retransmitting
void write_missing_sdp_seq_nums_into_sdram(
        uint32_t data[], ushort length, uint32_t start_offset){

    for(ushort offset=start_offset; offset < length; offset ++){
        missing_sdp_seq_num_sdram_address[
            data_written + (offset - start_offset)] = data[offset];
        //log_info("data writing into sdram is %d", data[offset]);
    }
    data_written += (length - start_offset);
}

//! entrance method for storing SDP seq nums into SDRAM
void store_missing_seq_nums(uint32_t data[], ushort length, bool first){
    uint32_t start_reading_offset = 1;
    if (first){
        missing_sdp_packets = data[1];
        final_seq_num = (
            (ITEMS_PER_DATA_PACKET - 2) +
            ((missing_sdp_packets  - 1) * (ITEMS_PER_DATA_PACKET - 1)));
        log_info("final seq num count is %d", final_seq_num);

        uint32_t size_of_data =
            ((missing_sdp_packets * ITEMS_PER_DATA_PACKET) *
            WORD_TO_BYTE_MULTIPLIER) + END_FLAG_SIZE;

        //log_info("doing first with xalloc of %d bytes", size_of_data);
        if(missing_sdp_seq_num_sdram_address != NULL){
            sark_xfree(sv->sdram_heap, missing_sdp_seq_num_sdram_address,
                       ALLOC_LOCK + ALLOC_ID + (sark_vec->app_id << 8));
            missing_sdp_seq_num_sdram_address = NULL;
        }
        missing_sdp_seq_num_sdram_address = sark_xalloc(
            sv->sdram_heap, size_of_data, 0,
            ALLOC_LOCK + ALLOC_ID + (sark_vec->app_id << 8));
        start_reading_offset = 2;
        log_info("address to write to is %d",
                 missing_sdp_seq_num_sdram_address);
    }
    
    // write data to sdram and update packet counter
    write_missing_sdp_seq_nums_into_sdram(data, length, start_reading_offset);
    missing_sdp_packets -= 1;
}

//! does the regeneration of data
void regenerate_data_for_seq_num(uint32_t seq_num){
    uint32_t start_value = seq_num * (ITEMS_PER_DATA_PACKET -1);
    data[0] = seq_num;

    if( final_seq_num == total_position){
        log_info("sending last seq num");
    }

    for (uint32_t position = 1; position < ITEMS_PER_DATA_PACKET; position++){
        data[position] = start_value;
        start_value +=1;
    }

}

//! sets off a DMA for retransmission stuff
void retransmission_dma_read(){
    // update dma pointer for oscillation
    dma_pointer = (dma_pointer + 1) % N_DMA_BUFFERS;

    // locate where we are in sdram
    uint32_t position_to_read_from =
        (position_for_retransmission * ITEMS_PER_DATA_PACKET);
    address_t data_sdram_position =
        &missing_sdp_seq_num_sdram_address[position_to_read_from];
    //log_info(" address to dma from is %d", data_sdram_position);
    //log_info(" dma pointer = %d", dma_pointer);
    //log_info("size to read is %d",
    //         ITEMS_PER_DATA_PACKET * WORD_TO_BYTE_MULTIPLIER);

    // set off dma
    //log_info("setting off dma");
    while (!spin1_dma_transfer(
            DMA_TAG_READ_FOR_RETRANSMISSION, data_sdram_position,
            (void *)dma_data[dma_pointer], DMA_READ,
            ITEMS_PER_DATA_PACKET * WORD_TO_BYTE_MULTIPLIER)){
        // do nothing when failing, just keep retrying. it'll work at
        // some point
        log_info("failing to set off dma transfer!");
    }
}

void the_dma_complete_callback(uint unused, uint tag){
    use(unused);

    // check tag and work accordingly
    //log_info("dma complete callback");
    if(tag == DMA_TAG_READ_FOR_RETRANSMISSION){

        //log_info("in retransmission mode of dma");
        uint32_t current_dma_buffer = dma_pointer;

        // set up next dma if needed
        position_for_retransmission += 1;
        uint32_t data_read =
            position_for_retransmission * ITEMS_PER_DATA_PACKET;
        //log_info("position for retransmission = %d",
        //         position_for_retransmission);
        log_info("read %d data, out of %d data", data_read, data_written);
        if (data_written > data_read){
            retransmission_dma_read();
        }
        
        // build flag for iterating through dma stuff and 
        bool finished = false;
        //log_info("read for regeneration and transmission");
        uint32_t position_in_read_data = 0;

        // iterate till we either find a end flag, or run out of dma buffer
        while(!finished && (position_in_read_data < ITEMS_PER_DATA_PACKET)){

            // get next seq num to regenerate
            uint32_t missing_seq_num =
                (uint32_t)dma_data[current_dma_buffer][position_in_read_data];
            if(missing_seq_num != END_FLAG){

                // regenerate data
                regenerate_data_for_seq_num(missing_seq_num);
                position_in_read_data += 1;
                total_position += 1;
                // send new data back to host
                send_data(data,
                          ITEMS_PER_DATA_PACKET * WORD_TO_BYTE_MULTIPLIER);
            }
            else{ // finished data send, tell host its done
               uint32_t end_data = END_FLAG;
               check=true;
               send_data(&end_data, 4);
               finished = true;
            }
        }
    }
    else if(tag == DMA_TAG_READ_FOR_TRANSMISSION){
        log_warning("really shouldn't be here. But later needs to plug "
                    "in functionality here for reading from SDRAM to build "
                    "entire protocol");
    }
    else{
        log_error("Got somewhere i shouldn't have!");
    }
}

//! sdp reception
void sdp(uint mailbox, uint port){
    //log_info("packet received");
    sdp_msg_pure_data *msg = (sdp_msg_pure_data *) mailbox;

    //log_info("received packet with code %d", msg->data[0]);

    // start the process of sending data
    if(msg->data[0] == SDP_COMMAND_FOR_SENDING_DATA){
        //log_info("starting the send of orginial data");
        spin1_msg_free(msg);
        start_data();
    }

    // start or continue to gather missing packet list
    else if(msg->data[0] == SDP_COMMAND_FOR_START_OF_MISSING_SDP_PACKETS ||
            msg->data[0] == SDP_COMMAND_FOR_MORE_MISSING_SDP_PACKETS){
        //log_info("starting resend mode");

        // reset state, as could be here from multiple attempts
        if(msg->data[0] == SDP_COMMAND_FOR_START_OF_MISSING_SDP_PACKETS){
            data_written= 0;
            missing_sdp_packets = 0;
            total_position = 0;
            position_for_retransmission = 0;
        }


        store_missing_seq_nums(
            msg->data,
            ((msg->length - LENGTH_OF_SDP_HEADER) / WORD_TO_BYTE_MULTIPLIER),
            msg->data[0] == SDP_COMMAND_FOR_START_OF_MISSING_SDP_PACKETS);
        //log_info("free message");
        spin1_msg_free(msg);

        // if got all missing packets, start retransmitting them to host
        if(missing_sdp_packets == 0){
        
            // packets all received, add finish flag for dma stoppage
            missing_sdp_seq_num_sdram_address[data_written + 1] = END_FLAG;
            data_written += 1;

            log_info("create dma buffers");
            // create the dma buffers when needed
            for (uint32_t i = 0; i < N_DMA_BUFFERS; i++) {
                dma_data[i] = (uint32_t*) spin1_malloc(
                    ITEMS_PER_DATA_PACKET * sizeof(uint32_t));
            }

            log_info("start retransmission");
            // start dma off  
            retransmission_dma_read();
        }
    }

    else{
        log_error("received unknown sdp packet");
    }
}

//! boiler plate: not really needed
void resume_callback() {
    time = UINT32_MAX;
}

//! setup
static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started\n");

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // Get the timing details and set up the simulation interface
    if (!simulation_initialise(
            data_specification_get_region(SYSTEM_REGION, address),
            APPLICATION_NAME_HASH, timer_period, &simulation_ticks,
            &infinite_run, SDP, DMA)) {
        return false;
    }

    // add callback for dma when dealing with retransmissions
    simulation_dma_transfer_done_callback_on(
        DMA_TAG_READ_FOR_RETRANSMISSION,
        the_dma_complete_callback);

    // read config params.
    address_t config_address = data_specification_get_region(
        CONFIG, address);
    bytes_to_write = config_address[MB];
    use_seq = config_address[ADD_SEQ];

    log_info("bytes to write is %d", bytes_to_write);

    // flags needed for sdp message to go via ethernet
    my_msg.tag = 1;                    // IPTag 1
    my_msg.dest_port = PORT_ETH;       // Ethernet
    my_msg.dest_addr = sv->eth_addr;   // Nearest Ethernet chip

    // fill in SDP source & flag fields
    my_msg.flags = 0x07;
    my_msg.srce_port = 3;
    my_msg.srce_addr = sv->p2p_addr;

    return true;
}

//! start
void c_main() {

    uint32_t timer_period;
    log_info("starting packet gatherer\n");

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    simulation_sdp_callback_on(SDP_PORT_FOR_SDP_PACKETS, sdp);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
