#define LOG_LEVEL 40 //debug

#undef PRODUCTION_CODE
#undef NDEBUG

#include "spin1_api.h"
#include <debug.h>
#include "common-typedefs.h"
#include "../common/db-typedefs.h"
#include "../common/memory_utils.h"
#include "../common/sdp_utils.h"

#include <data_specification.h>
#include <simulation.h>
#include <sark.h>
#include <circular_buffer.h>

// Globals

typedef enum regions_e {
    SYSTEM_REGION = 0, TRANSMISSIONS = 1, SDP_PORT_REGION = 2,
    DB_DATA_REGION = 3
} regions_e;

typedef enum callback_priority_e {
    SDP_PRIORITY=0, TIMER_TICK_PRIORITY = 1, USER_EVENT_PRIORITY = 2
} callback_priority_e;

typedef enum transmission_region_elements_e {
    HAS_KEY=0, KEY=1
} transmission_region_elements_e;

typedef enum sdp_port_region_elements_e {
    SDP_PORT_POSITION=0
} sdp_port_region_elements_e;

//! \data region elements
typedef enum string_region_elements_e {
    DATA_REGION_SIZE=0
} string_region_elements_e;


//! buffer holding sdp packets received
static circular_buffer sdp_buffer;


static uint32_t chip_x;
static uint32_t chip_y;
static uint32_t core_identifier;

//! bool to stop processing events
static bool processing_events = false;

//! if doing relational,
#ifdef DB_TYPE_RELATIONAL
    Table* tables = NULL;
    uint n_tables = 0;
#endif

//! memory stores
address_t currentQueryAddress;
address_t startQueryAddress;
address_t system_region;
address_t data_region;

//! copies of the sdp message
sdp_msg_t** msg_copies;
uint i = 0;

//round robin
uchar h_chip_x = 0;
uchar h_chip_y = 0;
uchar h_core = FIRST_LEAF-1; //-1 because of ++hcore later

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

// key data
uint32_t has_key = 0;
uint32_t key = 0;

// sdp port data
uint32_t sdp_port_num = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

static uint32_t QUEUE_SIZE = 128;

//! different functions used by different modes
#ifdef DB_TYPE_KEY_VALUE_STORE
    #ifdef DB_SUBTYPE_HASH_TABLE

        uint32_t hash(uchar* bytes, size_t size){
            #ifdef HASH_FUNCTION_DFJB
                uint32_t h = 5381;

                uint i = 0;
                for(uint i = 0; i < size; i++)
                    h = ((h << 5) + h) + bytes[i];
                return h;
            #endif
            #ifdef HASH_FUNCTION_XOR
                uint32_t h = 0x55555555;

                for(uint i = 0; i < size; i++){
                    h ^= bytes[i];
                    h = h << 5;
                }
                return h;
            #endif
            #ifdef HASH_FUNCTION_JENKINGS
                uint32_t hash, i;
                for(hash = i = 0; i < size; ++i)
                {
                    hash += bytes[i];
                    hash += (hash << 10);
                    hash ^= (hash >> 6);
                }
                hash += (hash << 3);
                hash ^= (hash >> 11);
                hash += (hash << 15);
                return hash;
            #endif
        }
    #endif
#endif

//! timer tick callback function
void update (uint ticks, uint b){
    use(ticks);
    use(b);

    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {
        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);
        return;
    }
}

//! sdp callback function
void sdp_packet_callback(register uint mailbox, uint port) {
    use(port);

    i = (i+1)%QUEUE_SIZE;
    register sdp_msg_t* m = msg_copies[i];
    sark_word_cpy(m, (sdp_msg_t*)mailbox, sizeof(sdp_hdr_t)+256);
    spin1_msg_free((sdp_msg_t*)mailbox);

    // If there was space, add packet to the ring buffer
    if (circular_buffer_add(sdp_buffer, (uint32_t)m)) {
        if (!processing_events) {
            processing_events = true;
            if(!spin1_trigger_user_event(0, 0)){
                log_error("Unable to trigger user event.");
            }
        }
    }
    else{
        log_error("Unable to add SDP packet to circular buffer.");
    }
}

//! user event
void process_requests(uint arg0, uint arg1){
    use(arg0);
    use(arg1);

    //uint i = 0;
    uint32_t mailbox;
    do {
        if (circular_buffer_get_next(sdp_buffer, &mailbox)) {

            sdp_msg_t* msg = (sdp_msg_t*)mailbox;

            spiDBQueryHeader* header = (spiDBQueryHeader*) &msg->cmd_rc;

            if(!header){
                log_info("NULL spiDBQueryHeader received");
                //spin1_msg_free(msg);
                //sark_free(msg);
                continue;
            }

        #ifdef DB_TYPE_KEY_VALUE_STORE

        if(header->cmd == PUT || header->cmd == PULL){
            putPullQuery* p = (putPullQuery*)header;

            log_info("%s, id %d", p->cmd == PUT ? "PUT" : "PULL", p->id);
            log_info("  info: %08x, data: %s", p->info, p->data);

            #ifdef DB_SUBTYPE_HASH_TABLE
                    uint32_t h = hash(p->data, k_size_from_info(p->info));

                    h_chip_x =((h & 0x00FF0000) >> 16) % CHIP_X_SIZE;
                    h_chip_y =((h & 0x0000FF00) >> 8)  % CHIP_Y_SIZE;
                    h_core  =((h & 0x000000FF) % NUMBER_OF_LEAVES) + FIRST_LEAF;
            #else
                if(header->cmd == PUT){
                    if(++h_core > LAST_LEAF){
                        h_core = FIRST_LEAF;
                        if(++h_chip_x >= CHIP_X_SIZE){
                            h_chip_x = 0;
                            if(++h_chip_y >= CHIP_Y_SIZE){
                                h_chip_y = 0;
                            }
                        }
                    }
                }
                else{ //PULL

                    if(msg->srce_port == PORT_ETH){ //msg came from host
                        //tell the other root cores to scan
                        set_srce_as_self(msg);

                        set_dest_xyp(msg, 0, 1, 1);
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                        set_dest_xyp(msg, 1, 0, 1);
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);

                        set_dest_xyp(msg, 1, 1, 1);
                        spin1_send_sdp_msg(msg, SDP_TIMEOUT);
                    }

                    //if we run out of root SDRAM, roll over
                    if(currentQueryAddress+sizeof(pullQuery) >=
                        startQueryAddress+ROOT_SDRAM_SIZE_BYTES){
                            log_info("Roll over...");
                            currentQueryAddress = startQueryAddress;
                    }

                    address_t a = append(&currentQueryAddress,
                                         p, sizeof(pullQuery));
                    if(!a){
                        log_error("Error storing pullQuery to SDRAM.");
                        continue;
                    }

                    //broadcast pointer to message over Multicast
                    while(!spin1_send_mc_packet(key, (uint)a, WITH_PAYLOAD)){
                        log_info("Attempting to send PULL MC packet again.");
                        spin1_delay_us(1);
                    }

                    //spin1_msg_free(msg);
                    continue;
                }
            #endif

            set_dest_xyp(msg, h_chip_x, h_chip_y, h_core);

            if(spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                //log_info("  Sent to (%d,%d,%d)", h_chip_x, h_chip_y, h_core);
            }
            else {
                log_error("  Unable to send query to (%d,%d,%d)",
                          p->data, h_chip_x, h_chip_y, h_core);
            }
        }
        #endif
        #ifdef DB_TYPE_RELATIONAL

        switch(header->cmd){
            case CREATE_TABLE:;
                log_info("CREATE");
                createTableQuery* q = (createTableQuery*) header;
                Table* t = &q->table;

                Table* newTable;

                if(getTable(tables, t->name)){
                    log_error("Table with name '%s' already exists.");
                    newTable = NULL;
                }
                else{
                    uint32_t row_size = 0;
                    for(uint32_t i = 0; i < t->n_cols; i++){
                        //round up to the closest power of 4
                        //as Spinnaker is word aligned
                        t->cols[i].size = ((t->cols[i].size + 3) / 4) * 4;
                        row_size += t->cols[i].size;
                    }
                    t->row_size = row_size;

                    newTable = (Table*)(data_region + n_tables * sizeof(Table));
                    write((address_t)newTable, t, sizeof(Table));

                    log_info("  Table '%s'-> %08x", newTable->name, newTable);
                    print_table(newTable);

                    n_tables++;
                }

                revert_src_dest(msg);

                msg->length = sizeof(sdp_hdr_t) + sizeof(Response_hdr);

                Response* response = (Response*)&msg->cmd_rc;
                response->id  = q->id;
                response->cmd = CREATE_TABLE;
                response->success = newTable ? true : false;
                response->x = chip_x;
                response->y = chip_y;
                response->p = core_identifier;

                if(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                    log_error("Unable to send CREATE_TABLE ack");
                }
                break;
            case INSERT_INTO:;
                log_info("INSERT_INTO");
                insertEntryQuery* insertE = (insertEntryQuery*) header;
                Entry e = insertE->e;

                //printEntry(&e);

                uint32_t dest_core = (e.row_id % 11) + FIRST_LEAF;

                if(e.type == UINT32){
                    log_info("INSERT_INTO '%s' - core %d  < (%s,%d) (integer)",
                             insertE->table_name, dest_core,
                             e.col_name, *e.value);
                }
                else{
                    log_info("INSERT_INTO '%s' - core %d  < (%s,%s) (varchar)",
                             insertE->table_name, dest_core,
                             e.col_name, e.value);
                }

                set_dest_chip(msg,spin1_get_chip_id());//same chip
                set_dest_core(msg,dest_core);

                while(!spin1_send_sdp_msg(msg, SDP_TIMEOUT)){
                    spin1_delay_us(2);
                    log_info("Attempting to send INSERT_INTO to %d again",
                             dest_core);
                }
                break;
            case SELECT:;
                log_info("SELECT");
                print_SELECT((selectQuery*)header);

                //store SELECT query message to SDRAM
                //so it can be read by other cores
                address_t a = append(&currentQueryAddress,
                                     (selectQuery*)header,
                                     sizeof(selectQuery));

                if(!a){
                    log_error("Error storing selectQuery to SDRAM.");
                    continue;
                }

                //broadcast pointer to message over Multicast
                while(!spin1_send_mc_packet(key, (uint)a, WITH_PAYLOAD)){
                    log_info("Attempting to send MC packet again.");
                    spin1_delay_us(1);
                }
                break;
            default:;
                //log_info("[Warning] cmd not recognized: %d with id %d",
                //         header->cmd, header->id);
                break;
        }
        #endif

       }
       else {
        processing_events = false;
       }
    }
    while (processing_events);
}

static bool initialize(uint32_t *timer_period) {
    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    log_info("DataSpecification address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read DataSpecification header");
        return false;
    }

    system_region = data_specification_get_region(SYSTEM_REGION, address);

    if (!simulation_read_timing_details(
            system_region, APPLICATION_NAME_HASH, timer_period)) {
        log_error("failed to read the system header");
        return false;
    }

    data_region = data_specification_get_region(DB_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    // clear the data region of any data
    uint32_t data_region_size = data_region[DATA_REGION_SIZE] / 4; // bytes to ints
    memory_utils_clear(data_region, data_region_size);

    address_t sdp_port_region =
        data_specification_get_region(SDP_PORT_REGION, address);
    sdp_port_num = sdp_port_region[SDP_PORT_POSITION];

    // Get the transmission details
    address_t mc_region = data_specification_get_region(
        TRANSMISSIONS, address);

    // get keys
    has_key = mc_region[HAS_KEY];
    key = mc_region[KEY];

    if (has_key == 1){
        log_info("I do have a key and it is %d", key);
    }
    else{
        log_info("I do not have a key");
    }

        msg_copies = (sdp_msg_t**)sark_alloc(QUEUE_SIZE, sizeof(sdp_msg_t*));
    for(uint i = 0; i < QUEUE_SIZE; i++){
        msg_copies[i] = (sdp_msg_t*)sark_alloc(1, sizeof(sdp_hdr_t)+256);
    }

    if(!msg_copies){
        log_error("Unable to allocate memory for msg_copies");
        rt_error(RTE_SWERR);
    }

    // build queue for sdp packets
    sdp_buffer = circular_buffer_initialize(QUEUE_SIZE);

    if(!sdp_buffer){
        rt_error(RTE_SWERR);
    }

    log_info("Initialization completed successfully!");
    return true;
}

void c_main(){

    // get the id of this core
    chip_x = (spin1_get_chip_id() & 0xFF00) >> 8;
    chip_y = spin1_get_chip_id() & 0x00FF;
    core_identifier  = spin1_get_core_id();

    // timer period
    uint32_t timer_period;

    // try initialize
    log_info("Initializing Root...");
    if (!initialize(&timer_period)) {
        log_info("Failed to initialize properly.");
        rt_error(RTE_SWERR);
    }

    #ifdef DB_TYPE_KEY_VALUE_STORE
        startQueryAddress = data_region;
    #endif
    #ifdef DB_TYPE_RELATIONAL
        tables = (Table*) data_region;

        startQueryAddress =
               data_region + sizeof(Table) * DEFAULT_NUMBER_OF_TABLES;
    #endif

    currentQueryAddress = startQueryAddress;

    //timer tick in microseconds
    spin1_set_timer_tick(timer_period);

    // Set up callback listening to SDP messages
    simulation_register_simulation_sdp_callback(
        &simulation_ticks, &infinite_run, SDP_PRIORITY);

    // register callbacks
    spin1_sdp_callback_on(sdp_port_num, sdp_packet_callback, SDP_PRIORITY);
    spin1_callback_on(TIMER_TICK, update, TIMER_TICK_PRIORITY);
    spin1_callback_on(USER_EVENT, process_requests, USER_EVENT_PRIORITY);

    simulation_run();
}