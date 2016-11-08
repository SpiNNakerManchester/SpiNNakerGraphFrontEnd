
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>

/*! multicast routing keys to communicate with neighbours */
uint my_key;
uint has_key = NULL;

/*! buffer used to store spikes */
static circular_buffer input_buffer;
static uint32_t current_payload;
static uint32_t current_key;

static uint32_t N_PACKETS_PER_EDGE = 14

//! weather specific data items
s3231 my_p = NULL;
s3231 my_v = NULL;
s3231 my_u = NULL;
uint32_t is_east_edge = NULL;
uint32_t is_north_east_edge = NULL;
uint32_t is_north_edge = NULL;
s3231 tdt = NULL;
s3231 dx = NULL;
s3231 dy = NULL;
s3231 fsdx = NULL;
s3231 fsdy = NULL;
s3231 alpha = NULL;

// weather receive data items
s3231 east_elements[] = {NULL, NULL, NULL, NULL, NULL, NULL, NULL}
s3231 north_east_elements[] = {NULL, NULL, NULL, NULL, NULL, NULL, NULL}
s3231 north_elements[] = {NULL, NULL, NULL, NULL, NULL, NULL, NULL}

//! neighbour keys
uint32_t north_key = NULL;
uint32_t north_east_key = NULL;
uint32_t east_key = NULL;

//! recorded data items
uint32_t size_written = 0;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t time = 0;
static s3231 CONVERTER = 2147483647.0;
address_t address = NULL;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

// value for turning on and off interrupts
uint cpsr = 0;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    TRANSMISSIONS,
    NEIGHBOUR_KEYS,
    INIT_STATE_VALUES,
    FINAL_STATES
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, TIMER = 2
} callback_priorities;

//! human readable values for true and false
typedef enum booleans{
    TRUE = 0, FALSE = 1
} booleans;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;

//! human readable definitions of each element in the initial state
//! region
typedef enum initial_state_region_elements {
    U_INIT_TOP_BIT = 0, U_INIT_POINT_BIT = 1, V_INIT_TOP_BIT = 2,
    V_INIT_POINT_BIT = 3, P_INIT_TOP_BIT = 4, P_INIT_POINT_BIT = 5,
    AT_EAST_EDGE = 6,
        EAST_HARD_CODED_U_TOP_BIT = 7, EAST_HARD_CODED_U_POINT_BIT = 8,
        EAST_HARD_CODED_V_TOP_BIT = 9, EAST_HARD_CODED_V_POINT_BIT = 10,
        EAST_HARD_CODED_P_TOP_BIT = 11, EAST_HARD_CODED_P_POINT_BIT = 12,
    AT_NORTH_EAST_EDGE = 13,
        NORTH_EAST_HARD_CODED_U_TOP_BIT = 14,
        NORTH_EAST_HARD_CODED_U_POINT_BIT = 15,
        NORTH_EAST_HARD_CODED_V_TOP_BIT = 16,
        NORTH_EAST_HARD_CODED_V_POINT_BIT = 17,
        NORTH_EAST_HARD_CODED_P_TOP_BIT = 18,
        NORTH_EAST_HARD_CODED_P_POINT_BIT = 19,
    AT_NORTH_EDGE = 20,
        NORTH_HARD_CODED_U_TOP_BIT = 21,
        NORTH_HARD_CODED_U_FLOAT_BIT = 22,
        NORTH_HARD_CODED_V_TOP_BIT = 23,
        NORTH_HARD_CODED_V_FLOAT_BIT = 24,
        NORTH_HARD_CODED_P_TOP_BIT = 25,
        NORTH_HARD_CODED_P_FLOAT_BIT = 26,
    TDT_TOP_BIT = 27, TDT_FLOAT_BIT = 28,
    DX_TOP_BIT = 29, DX_FLOAT_BIT = 30,
    DY_TOP_BIT = 31, DY_FLOAT_BIT = 32,
    FSDX_TOP_BIT = 33, FSDX_FLOAT_BIT = 34,
    FSDY_TOP_BIT = 35, FSDY_FLOAT_BIT = 36,
    ALPHA_TOP_BIT = 37, ALPHA_FLOAT_BIT = 38
} initial_state_region_elements;

//! human readable for the key allocation offset for the data bits
typedef enum key_offsets {
    U_TOP_BIT = 0, U_FLOAT_BIT = 1, V_TOP_BIT = 2, V_FLOAT_BIT = 3,
    P_TOP_BIT = 4, P_FLOAT_BIT = 5, Z_TOP_BIT = 6, Z_FLOAT_BIT = 7, 
    H_TOP_BIT = 8, H_FLOAT_BIT = 9, CV_TOP_BIT = 10, CV_FLOAT_BIT = 11, 
    CU_TOP_BIT = 12, CU_FLOAT_BIT = 13
} key_offsets;

//! human readable for the location in a array for element bits
typedef enum element_offsets {
    U = 0, V = 1, P = 2, Z = 3, H = 4, CV = 5, CU = 6
} element_offsets;

//! human readable for the location of neighbours keys in sdram
typedef enum neighbour_keys {
    SOUTH = 0, SOUTH_WEST = 1, WEST = 2
} neighbour_keys;


/****f* weather.c/receive_data
 *
 * SUMMARY
 *  This function is used as a callback for packet received events.
 * receives data from 8 neighbours and updates the states params
 *
 * SYNOPSIS
 *  void receive_data (uint key, uint payload)
 *
 * INPUTS
 *   uint key: packet routing key - provided by the RTS
 *   uint payload: packet payload - provided by the RTS
 *
 * SOURCE
 */
void receive_data(uint key, uint payload) {
    //log_info("the key i've received is %d\n", key);
    //log_info("the payload i've received is %d\n", payload);
    // If there was space to add data to incoming data queue
    if (!circular_buffer_add(input_buffer, key)) {
        log_info("Could not add state");
    }
    if (!circular_buffer_add(input_buffer, payload)) {
        log_info("Could not add state");
    }
}

void convert_inputs_to_s3231_elements(
        s3231 *components, s3231 *final_elements, ){
    if (components[U_TOP_BIT] != NULL &&
                components[U_FLOAT_BIT] != NULL){
            north_u = translate_to_s3231_value(
                components[U_TOP_BIT], components[U_FLOAT_BIT]);
        }
        else{
            log_error("missing a packet for the u from the north")
        }
}

//! \brief puts the element in the correct location
//! \param[in] elements: the list of which this payload is going to reside
void process_key_payload(s3231 *elements){
    // get the offset in the array from the key
    offset = current_key & 0xFFFFFFF0;

    // add the element to the correct offset
    elements[offset] = (s3231) current_payload;
}

void read_input_buffer(){

    circular_buffer_print_buffer(input_buffer);

    // calculate how many packets should be in the buffer
    uint32_t n_packets_per_timer_tick = 0
    if (is_east_edge == FALSE){
        n_packets_per_timer_tick + N_PACKETS_PER_EDGE;
    }
    if (is_north_edge == FALSE){
        n_packets_per_timer_tick + N_PACKETS_PER_EDGE;
    }
    if (is_north_east_edge == FALSE){
        n_packets_per_timer_tick + N_PACKETS_PER_EDGE;
    }

    while(circular_buffer_size(input_buffer) < n_packets_per_timer_tick){
        for(uint32_t counter = 0; counter < 10000, counter++){
            //do nothing
        }
        log_info("size of buffer is %d whereas it should be %d",
                 circular_buffer_size(input_buffer), n_packets_per_timer_tick)
    }
    log_info("running past buffer length");

    cpsr = spin1_int_disable();
    circular_buffer_print_buffer(input_buffer);

    // linked to the key offset map
    s3231 east_components[] = {
        NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
        NULL, NULL, NULL}
        
    // linked to the key offset map
    s3231 north_east_components[] = {
        NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
        NULL, NULL, NULL}

    // linked to the key offset map
    s3231 north_components[] = {
        NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
        NULL, NULL, NULL}

    // pull payloads and keys from input_buffer.
    // translate into s3231 elements
    for (uint32_t counter = 0; counter < n_packets_per_timer_tick; counter ++){
        bool success1 = circular_buffer_get_next(
            input_buffer, &current_payload);
        bool success2 = circular_buffer_get_next(
            input_buffer, &current_key);
        if (success1 && success2){
            key_mask = 0xF;
            masked_key = current_key & key_mask;
            if (masked_key == north_key){
                process_key_payload(north_components);
            }
            else if (masked_key == north_east_key){
                process_key_payload(north_east_components);
            }
            else if (masked_key == east_key){
                process_key_payload(east_components);
            }}
        else{
            log_debug("couldn't read state from my neighbours.");
        }

    }
    spin1_mode_restore(cpsr);
    
    // convert 2 ints into s3231 for the correct locations.
    // handle north first
    if (!is_north_edge){
        convert_inputs_to_s3231_elements(north_components, north_elements);
    }
    if (!is_north_east_edge){
        convert_inputs_to_s3231_elements(
            north_east_components, north_east_elements);
    }
    if (!is_east_edge){
        convert_inputs_to_s3231_elements(east_components, east_elements);
    }
}

void record_state(){
    //* record my state via sdram
    address_t record_region =
        data_specification_get_region(RECORDED_DATA, address);
    uint8_t* record_space_address = (uint8_t*) record_region;
    record_space_address = record_space_address + 4 + size_written;
    spin1_memcpy(record_space_address, &my_state, 4);
    size_written = size_written + 4;
    log_debug("space written is %d", size_written);
    log_debug("recorded my state \n");
}

void send_state(){
    // reset for next iteration
    alive_states_recieved_this_tick = 0;
    dead_states_recieved_this_tick = 0;

    // send my new state to the simulation neighbours
    log_debug("sending my state of %d via multicast with key %d",
              my_state, my_key);
    while (!spin1_send_mc_packet(my_key, my_state, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

    log_debug("sent my state via multicast");
}

/****f* weather.c/update
 *
 * SUMMARY
 *
 * SYNOPSIS
 *  void update (uint ticks, uint b)
 *
 * SOURCE
 */
void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    log_info("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {

        // update recording data
        address_t record_region =
            data_specification_get_region(FINAL_STATES, address);
        uint8_t* record_space_address = (uint8_t*) record_region;
        log_info("wrote final store of %d bytes", size_written);
        spin1_memcpy(record_space_address, &size_written, 4);

        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        return;
    }

    read_input_buffer();

    // find my next state
    next_state();

    send_states();

        //record_state();
}

//! \brief this method is to catch strange behaviour
//! \param[in] key: the key being received
//! \param[in] unknown: second arg with no state. set to zero by default
void receive_data_void(uint key, uint unknown) {
    use(key);
    use(unknown);
    log_error("this should never ever be done\n");
}

void set_key(address_t address){
    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    has_key = transmission_region_address[HAS_KEY];
    if (has_key == TRUE) {
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    }
}

//! \brief function to read in a s3231 from 2 ints
//! \param[in] top_bit_offset: the top bit of the s3231 int
//! \param[in] float_bit_offset: the float bit of the s3231 int
//! \param[in] region_address: the 
//! \param[out] the s3231 value
s3231 read_in_s3231_value_sdram(
        uint32_t top_bit_offset, uint32_t float_bit_offset,
        address_t region_address){
    s3231 my_top_bit = ((s3231)region_address[top_bit_offset]) << 32;
    s3231 my_point_bit = (s3231) region_address[float_bit_offset];
    my_value = my_top_bit + my_point_bit;
    return my_value;
}

//! \brief function to read in a s3231 from 2 ints
//! \param[in] top_bit: the top bit of the s3231 int
//! \param[in] float_bit: the float bit of the s3231 int
//! \param[out] the s3231 value
s3231 translate_to_s3231_value(uint32_t top_bit, uint32_t float_bit){
    s3231 my_top_bit = ((s3231)top_bit) << 32;
    s3231 my_point_bit = (s3231)float_bit;
    my_value = my_top_bit + my_point_bit;
    return my_value;
}

void set_init_states(address_t address){
    // read in the initial states
    // read my state
    address_t my_state_region_address = data_specification_get_region(
        INIT_STATE_VALUES, address);

    // u
    my_u = read_in_s3231_value_sdram(
        U_INIT_TOP_BIT, U_INIT_POINT_BIT, my_state_region_address);

    // v
    my_v = read_in_s3231_value_sdram(
        V_INIT_TOP_BIT, V_INIT_POINT_BIT, my_state_region_address);

    // p
    my_p = read_in_s3231_value_sdram(
        P_INIT_TOP_BIT, P_INIT_POINT_BIT, my_state_region_address);

    // at east edge
    is_east_edge = my_state_region_address[AT_EAST_EDGE];
    is_north_east_edge = my_state_region_address[AT_NORTH_EAST_EDGE];
    is_north_edge = my_state_region_address[AT_NORTH_EDGE];

    if (is_east_edge){

        // hard_coded "received" u value
        east_elements[U] = read_in_s3231_value_sdram(
            EAST_HARD_CODED_U_TOP_BIT, EAST_HARD_CODED_U_POINT_BIT,
            my_state_region_address);

        // the hard coded "received" v value
        east_elements[V] = read_in_s3231_value_sdram(
            EAST_HARD_CODED_V_TOP_BIT, EAST_HARD_CODED_V_POINT_BIT,
            my_state_region_address);

        // the hard coded "received" p value
        east_elements[P] = read_in_s3231_value_sdram(
            EAST_HARD_CODED_P_TOP_BIT, EAST_HARD_CODED_P_POINT_BIT,
            my_state_region_address);
    }

    if (is_north_east_edge){

        // hard_coded "received" u value
        north_east_elements[U] = read_in_s3231_value_sdram(
            NORTH_EAST_HARD_CODED_U_TOP_BIT, NORTH_EAST_HARD_CODED_U_POINT_BIT,
            my_state_region_address);

        // the hard coded "received" v value
        north_east_elements[V] = read_in_s3231_value_sdram(
            NORTH_EAST_HARD_CODED_V_TOP_BIT, NORTH_EAST_HARD_CODED_V_POINT_BIT,
            my_state_region_address);

        // the hard coded "received" p value
        north_east_elements[P] = read_in_s3231_value_sdram(
            NORTH_EAST_HARD_CODED_P_TOP_BIT, NORTH_EAST_HARD_CODED_P_POINT_BIT,
            my_state_region_address);
    }

    if (is_north_edge){

        // hard_coded "received" u value
        north_elements[U] = read_in_s3231_value_sdram(
            NORTH_HARD_CODED_U_TOP_BIT, NORTH_HARD_CODED_U_FLOAT_BIT,
            my_state_region_address);

        // the hard coded "received" v value
        north_elements[V] = read_in_s3231_value_sdram(
            NORTH_HARD_CODED_V_TOP_BIT, NORTH_HARD_CODED_V_FLOAT_BIT,
            my_state_region_address);

        // the hard coded "received" p value
        north_elements[V] = read_in_s3231_value_sdram(
            NORTH_HARD_CODED_P_TOP_BIT, NORTH_HARD_CODED_P_FLOAT_BIT,
            my_state_region_address);
    }

    tdt = read_in_s3231_value_sdram(
        TDT_TOP_BIT, TDT_FLOAT_BIT, my_state_region_address);

    dx = read_in_s3231_value_sdram(
        DX_TOP_BIT, DX_FLOAT_BIT, my_state_region_address);

    dy = read_in_s3231_value_sdram(
        DY_TOP_BIT, DY_FLOAT_BIT, my_state_region_address);

    fsdx = read_in_s3231_value_sdram(
        FSDX_TOP_BIT, FSDX_FLOAT_BIT, my_state_region_address);

    fsdy = read_in_s3231_value_sdram(
        FSDY_TOP_BIT, FSDY_FLOAT_BIT, my_state_region_address);

    alpha = read_in_s3231_value_sdram(
        ALPHA_TOP_BIT, ALPHA_FLOAT_BIT, my_state_region_address);
    )

    // print the data items
    log_info("")
}

void set_neighbour_keys(address_t address){
    
    address_t my_neighbour_state_region_address =
        data_specification_get_region(NEIGHBOUR_INITIAL_STATES, address);
    north_key = my_neighbour_state_region_address[SOUTH];
    north_east_key = my_neighbour_state_region_address[SOUTH_WEST];
    east_key = my_neighbour_state_region_address[WEST];
}

static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started\n");

    // Get the address this core's DTCM data starts at from SRAM
    address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // Get the timing details and set up the simulation interface
    if (!simulation_initialise(
            data_specification_get_region(SYSTEM_REGION, address),
            APPLICATION_NAME_HASH, timer_period, &simulation_ticks,
            &infinite_run, NULL, NULL, NULL)) {
        return false;
    }

    // find the key to use
    set_key(address);

    // read in initials states
    set_init_states(address);

    // read neighbour keys
    set_neighbour_keys(address);

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(512);
    if (input_buffer == 0){
        return false;
    }
    log_info("input_buffer initialised");

    return true;


}

/****f* weather.c/c_main
 *
 * SUMMARY
 *  This function is called at application start-up.
 *  It is used to register event callbacks and begin the simulation.
 *
 * SYNOPSIS
 *  int c_main()
 *
 * SOURCE
 */
void c_main() {
    log_info("starting weather cell\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        log_error("Error in initialisation - exiting!");
        rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_info("setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
