
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <stdbool.h>
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>
#include <string.h>
#include <recording.h>

/*! multicast routing keys to communicate with neighbours */
uint my_key;
uint has_key;

//! flag that tells the timer tick which data to deal with
uint is_cv_or_p_calculation;

/*! buffer used to store spikes */
static circular_buffer input_buffer;
static uint32_t current_payload;
static uint32_t current_key;

static uint32_t key_mask;

static uint32_t SIZE_OF_DATA_ITEM = 4;

//! The number of clock ticks to back off before starting the timer, in an
//! attempt to avoid overloading the network
static uint32_t window_offset;
static uint32_t time_between_spikes;
static uint32_t expected_time;

//! weather specific data items
float my_current_p;
float my_current_v;
float my_current_u;
float my_old_p;
float my_old_v;
float my_old_u;
float my_new_p;
float my_new_v;
float my_new_u;
float my_cv;
float my_cu;
float my_z;
float my_h;

//! constants
float dx;
float dy;
float fsdx;
float fsdy;
float alpha;
float tdts8;
float tdtsdx;
float tdtsdy;
float tdt2s8;
float tdt2sdx;
float tdt2sdy;

// weather receive data items
float east_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float north_east_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float north_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float north_west_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float west_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float south_west_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float south_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
float south_east_elements[] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

//! neighbour keys
uint32_t north_key;
uint32_t north_east_key;
uint32_t east_key;
uint32_t north_west_key;
uint32_t west_key;
uint32_t south_west_key;
uint32_t south_key;
uint32_t south_east_key;

//! recorded data items
static uint32_t recording_flags = 0;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t time = 0;
address_t address = NULL;

//! control flag for exiting if stuck in busy loop waiting for packets
static uint32_t told_to_exit_flag = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

// value for turning on and off interrupts
uint cpsr = 0;

// optimisation for doing multiplications in the logic code.
static const float POINT_5 = 0.5;

// optimisation for doing multiplications in the logic code.
static const float POINT_025 = 0.25;

// optimisation for doing divide in the logic code.
static const uint32_t EIGHT = 8;

//! how many entries in the ring buffer that there should be per timer tick

static uint32_t N_PACKETS_PER_CV_CU_H_Z_STATE_SPACE = 3 * 8 * 2;
static uint32_t N_PACKETS_PER_P_U_V_STATE_SPACE = 4 * 8 * 2;

static const uint CV_CU_Z_H = 0;
static const uint P_U_V = 1;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION = 0,
    TRANSMISSIONS = 1,
    TIMING_DATA = 2,
    NEIGHBOUR_KEYS = 3,
    INIT_STATE_VALUES = 4,
    FINAL_STATES = 5,
    PROVENANCE = 6
} regions_e;

typedef enum timing_data_elements{
    TIME_OFFSET = 0, TIME_BETWEEN_PACKETS = 1
} timing_data_elements;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, SDP = 0, TIMER = 2
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;

//! \brief a possible way to avoid reading in issues.
typedef struct init_data_t{
    // my values
    float my_current_u; float my_current_v; float my_current_p;
    // neighbour values
    float north_u; float north_v; float north_p;
    float north_east_u; float north_east_v; float north_east_p;
    float east_u; float east_v; float east_p;
    float south_east_u; float south_east_v; float south_east_p;
    float south_u; float south_v; float south_p;
    float south_west_u; float south_west_v; float south_west_p;
    float west_u; float west_v; float west_p;
    float north_west_u; float north_west_v; float north_west_p;
    // constants
    uint32_t dx; uint32_t dy; float fsdx; float fsdy;
    float alpha; float tdts8; float tdtsdx; float tdtsdy; float tdt2s8;
    float tdt2sdx; float tdt2sdy;
    // offset fix
    uint32_t random_backoff;
}init_data_t;

//! human readable for the location in a array for element bits
typedef enum element_offsets {
    U = 0, V = 1, P = 2, Z = 3, H = 4, CV = 5, CU = 6
} element_offsets;

//! human readable for the location of keys in sdram
typedef enum key_order {
    SOUTH = 0, SOUTH_WEST = 1, WEST = 2, NORTH_WEST = 3, NORTH = 4,
    NORTH_EAST = 5, EAST = 6, SOUTH_EAST = 7, KEY_MASK = 8
} key_order;

//! \brief converts a int to a float via bit wise conversion
//! \param[in] y: the int to convert
//! \param[out] the converted float
static inline float int_to_float( int data){
    union { float x; int y; } cast_union;
    cast_union.y = data;
    return cast_union.x;
}


static inline int float_to_int( float data){
    union { float x; int y; } cast_union;
    cast_union.x = data;
    return cast_union.y;
}

//! \brief print the constants of the vertex
void print_constants(){
    /*
    log_info("doing constants");
    
    // create list of things to print
    float to_print_items[] = {
        dx, dy, fsdx, fsdy, alpha, tdts8, tdtsdx, tdtsdy, tdt2s8, tdt2sdx, 
        tdt2sdy};
        
    // create list of names of params
    const char *to_print_strings[11];
    to_print_strings[0] = "dx";
    to_print_strings[1] = "dy";
    to_print_strings[2] = "fsdx";
    to_print_strings[3] = "fsdy";
    to_print_strings[4] = "alpha";
    to_print_strings[5] = "tdts8";
    to_print_strings[6] = "tdtsdx";
    to_print_strings[7] = "tdtsdy";
    to_print_strings[8] = "tdt2s8";
    to_print_strings[9] = "tdt2sdx";
    to_print_strings[10] = "tdt2sdy";
    
    
    for(int position = 0; position < 11; position ++){
        log_info(
            "%s = %x", to_print_strings[position],
            (int) to_print_items[position]);
    }
    log_info("end constants");
    */
}

void force_exit_function(address_t provenance_region){
    told_to_exit_flag = 1;
    log_info("been killed");
}

//! \brief print my local states
void print_my_states(){
    log_info("my_current_u = %x", float_to_int(my_current_u));
    log_info("my_current_v = %x", float_to_int(my_current_v));
    log_info("my_current_p = %x", float_to_int(my_current_p));
    log_info("my key = %d", my_key);
}

//! \brief print a set of elements for u,v,p
//! \param[in] elements_to_print: the array of elements to print elements of
//! \param[in] name: the name of the set of elements.
void print_a_set_of_elements(float *elements_to_print, char* name){

    float to_print_items[] = {
        elements_to_print[U], elements_to_print[V], elements_to_print[P],
        elements_to_print[Z], elements_to_print[H], elements_to_print[CV],
        elements_to_print[CU]};
    const char *to_print_strings[7];

    char copy_name1[80];
    char copy_name2[80];
    char copy_name3[80];
    char copy_name4[80];
    char copy_name5[80];
    char copy_name6[80];
    char copy_name7[80];
    

    to_print_strings[0] = strcat(strcpy(copy_name1, name), ":u");
    to_print_strings[1] = strcat(strcpy(copy_name2, name), ":v");
    to_print_strings[2] = strcat(strcpy(copy_name3, name), ":p");
    to_print_strings[3] = strcat(strcpy(copy_name4, name), ":z");
    to_print_strings[4] = strcat(strcpy(copy_name5, name), ":h");
    to_print_strings[5] = strcat(strcpy(copy_name6, name), ":cv");
    to_print_strings[6] = strcat(strcpy(copy_name7, name), ":cu");
    for(int position = 0; position < 7; position ++){
        log_info(
            "%s = %x", to_print_strings[position],
            float_to_int(to_print_items[position]));
    }
}

//! \brief prints the set of elements from neighbour locations.
void print_elements(){
    char name[11];
    strcpy(name, "north");
    print_a_set_of_elements(north_elements, name);
    strcpy(name, "north_east");
    print_a_set_of_elements(north_east_elements, name);
    strcpy(name, "east");
    print_a_set_of_elements(east_elements, name);
    strcpy(name, "south_east");
    print_a_set_of_elements(south_east_elements, name);
    strcpy(name, "south");
    print_a_set_of_elements(south_elements, name);
    strcpy(name, "south_west");
    print_a_set_of_elements(south_west_elements, name);
    strcpy(name, "west");
    print_a_set_of_elements(west_elements, name);
    strcpy(name, "north_west");
    print_a_set_of_elements(north_west_elements, name);
}


//! \brief method for receiving multicast packets with payloads
//! \param[in] key: the multicast key
//! \param[in] payload: the multicast payload.
void receive_data(uint key, uint payload) {
    // If there was space to add data to incoming data queue
    if (!circular_buffer_add(input_buffer, key)) {
        log_error("Could not add state");
    }
    if (!circular_buffer_add(input_buffer, payload)) {
        log_error("Could not add state");
    }
}

//! \brief puts the element in the correct location
//! \param[in] elements: the list of which this payload is going to reside
void process_key_payload(float *elements, uint32_t *has_flag_elements,
                         const char* direction){
    // get the offset in the array from the key
    uint32_t offset = current_key & 0x00000007;

    if (offset > 6){
        log_error(
            "got wrong offset. The offset i got from key %d is %d The "
            "payload assocated with this key was %d",
            current_key, offset, current_payload);
        rt_error(RTE_SWERR);
    }

    // add the element to the correct offset with a reinterpret cast to float
    elements[offset] = int_to_float(current_payload);

    log_info("The data for %s element %d is %x",
             direction, offset, current_payload);
    has_flag_elements[offset] = 1;
}


//! \brief reads in the ring buffer to get all the packets needed for the run
void read_input_buffer(){

    uint32_t last_seen_size = 0;
    uint32_t current_buffer_size;

    // deduce number of elements that should be in the input buffer based on
    // its function this timer tick (which state in the state space)
    uint n_elements_to_see = 0;
    if (is_cv_or_p_calculation == CV_CU_Z_H){
        n_elements_to_see = N_PACKETS_PER_CV_CU_H_Z_STATE_SPACE;
    }
    else{
        n_elements_to_see = N_PACKETS_PER_P_U_V_STATE_SPACE;
    }

    // read in input buffers
    while(circular_buffer_size(input_buffer) < n_elements_to_see){
        current_buffer_size = circular_buffer_size(input_buffer);
        for(uint32_t counter=0; counter < 10000; counter++){
            //do nothing
        }

        if (current_buffer_size != last_seen_size){
            log_info(
                "size of buffer is %d whereas it should be %d",
                current_buffer_size, n_elements_to_see);
            last_seen_size = current_buffer_size;
        }
    }

    //log_info("running past buffer length");

    cpsr = spin1_int_disable();
    //circular_buffer_print_buffer(input_buffer);

    // linked to the key offset map
    uint32_t has_east_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_north_east_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_north_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_north_west_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_west_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_south_west_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_south_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // linked to the key offset map
    uint32_t has_south_east_components[] = {
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};

    // pull payloads and keys from input_buffer.
    // translate into float elements
    for (uint32_t counter = 0; counter < n_elements_to_see / 2;
            counter ++){
        bool success1 = circular_buffer_get_next(
            input_buffer, &current_key);
        bool success2 = circular_buffer_get_next(
            input_buffer, &current_payload);
        if (success1 && success2){

            // deduce what the base key is
            uint32_t masked_key = current_key & key_mask;

            // process into the correct location
            if (masked_key == north_key){
                process_key_payload(
                    north_elements, has_north_components, "N");
            }
            else if (masked_key == north_east_key){
                process_key_payload(
                    north_east_elements, has_north_east_components, "NE");
            }
            else if (masked_key == east_key){
                process_key_payload(east_elements, has_east_components, "E");
            }
            else if (masked_key == south_east_key){
                process_key_payload(
                    south_east_elements, has_south_east_components, "SE");
            }
            else if (masked_key == south_key){
                process_key_payload(south_elements, has_south_components, "S");
            }
            else if (masked_key == south_west_key){
                process_key_payload(
                    south_west_elements, has_south_west_components, "SW");
            }
            else if (masked_key == north_west_key){
                process_key_payload(
                    north_west_elements, has_north_west_components, "NW");
            }
            else if (masked_key == west_key){
                process_key_payload(west_elements, has_west_components, "W");
            }
        }
        else{
            log_info("couldn't read state from my neighbours.");
        }
    }
    spin1_mode_restore(cpsr);
}

//! \brief records the data into the recording region
void record_state(){
    // record my state via sdram
    recording_record(0, &my_current_p, SIZE_OF_DATA_ITEM);
    recording_record(0, &my_current_u, SIZE_OF_DATA_ITEM);
    recording_record(0, &my_current_v, SIZE_OF_DATA_ITEM);
    recording_record(0, &my_cu, SIZE_OF_DATA_ITEM);
    recording_record(0, &my_cv, SIZE_OF_DATA_ITEM);
    recording_record(0, &my_z, SIZE_OF_DATA_ITEM);
    recording_record(0, &my_h, SIZE_OF_DATA_ITEM);
    recording_do_timestep_update(time);
    //log_info("recorded my state \n");
}

//! \brief sends packet and waits the hang time, ensuring spread during the
//! allocated time frame (this should be encapsulated into the sim interface
void send_packet(uint32_t key, uint payload){

    // Wait until the expected time to send
    while (tc[T1_COUNT] > expected_time) {
        if(told_to_exit_flag == 1){
            return;
        }
        // Do Nothing
    }

    // Send the packet
    while (!spin1_send_mc_packet(key, payload, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }
}


//! \brief sends the cu, cv, h, and z elements to their neighbours for their
//! second phase computation.
void send_cu_cv_h_z_states(){
    // send my new state to the simulation neighbours
    float elements_to_send[4];
    elements_to_send[0] = my_z;
    elements_to_send[1] = my_h;
    elements_to_send[2] = my_cv;
    elements_to_send[3] = my_cu;

    // key offsets for cv cu z h
    int key_offset[4] = {3, 4, 5, 6};

    const char *to_print_strings[4];
    to_print_strings[0] = "my_z";
    to_print_strings[1] = "my_h";
    to_print_strings[2] = "my_cv";
    to_print_strings[3] = "my_cu";

    // Wait till my place in the tdma agenda
    uint32_t agenda_start_time = tc[T1_COUNT] - window_offset;
    while (tc[T1_COUNT] > agenda_start_time) {
        if (told_to_exit_flag == 1){
            return;
        }
    }

    for(uint32_t position = 0; position < 4; position++){

        // log what we're firing
        uint32_t this_data_key = my_key + key_offset[position];
        log_info(
            "firing packet %s with value %x with key %d",
            to_print_strings[position],
            float_to_int(elements_to_send[position]), this_data_key);

        // Set the next expected time to wait for between spike sending
        expected_time = tc[T1_COUNT] - time_between_spikes;

        send_packet(this_data_key, float_to_int(elements_to_send[position]));
    }
    log_info("sent my states via multicast");
}

//! \brief sends the p,u,v elements to their neighbours for their first phase
//! computation
void send_p_u_v_states(){

    // send my new state to the simulation neighbours
    float elements_to_send[3];
    elements_to_send[0] = my_current_u;
    elements_to_send[1] = my_current_v;
    elements_to_send[2] = my_current_p;

    const char *to_print_strings[3];

    to_print_strings[0] = "my_current_u";
    to_print_strings[1] = "my_current_v";
    to_print_strings[2] = "my_current_p";

    // Wait till my place in the tdma agenda
    uint32_t agenda_start_time = tc[T1_COUNT] - window_offset;
    while (tc[T1_COUNT] > agenda_start_time) {
        if (told_to_exit_flag == 1){
            return;
        }
    }

    for(uint32_t position = 0; position < 3; position++){

        // log what we're firing
        uint32_t this_data_key = my_key + position;
        log_info(
            "firing packet %s with value %x with key %d",
            to_print_strings[position],
            float_to_int(elements_to_send[position]), this_data_key);

        // Set the next expected time to wait for between spike sending
        expected_time = tc[T1_COUNT] - time_between_spikes;

        send_packet(this_data_key, float_to_int(elements_to_send[position]));
    }
    log_info("sent my states via multicast");
}


//! \brief calculates the cu for this atom
void calculate_cu(){
    my_cu = POINT_5 * (my_current_p + south_elements[P]) * my_current_u;
    log_info("cu bits %x, %x, %x",
             float_to_int(my_current_p), float_to_int(south_elements[P]),
             float_to_int(my_current_u));
}

//! \brief calculates the cv for this atom
void calculate_cv(){
    my_cv = POINT_5 * (my_current_p + west_elements[P]) * my_current_v;
}

//! \brief calculates the z for this atom
void calculate_z(){
    float numerator_bit =
        (fsdx * (my_current_v - south_elements[V]) - fsdy *
        (my_current_u - west_elements[U]));
    float denominator_bit =
        (south_west_elements[P] + west_elements[P] + my_current_p +
         south_elements[P]);
    my_z = numerator_bit / denominator_bit;
}

//! \brief calculates the h for this atom
void calculate_h(){
    my_h = my_current_p + POINT_025 * (
        north_elements[U] * north_elements[U] + my_current_u * my_current_u +
        east_elements[V] * east_elements[V] + my_current_v * my_current_v);
}

//! \brief calculates the new p value based off other values
void calculate_new_p(float current_tdtsdx, float current_tdtsdy){
    my_new_p = my_old_p - current_tdtsdx * (north_elements[CU] - my_cu) -
        current_tdtsdy * (east_elements[CV] - my_cv);
}


//! \brief calculates the new v value based off other values
void calculate_new_v(float current_tdts_8, float current_tdtsdy){
    my_new_v = my_old_v - current_tdts_8 * (north_elements[Z] + my_z) *
        (north_elements[CU] + my_cu + west_elements[CU] +
         north_west_elements[CU]) -
         current_tdtsdy * (my_h - west_elements[H]);
    //log_info("%x, %x, %x, %x, %x, %x, %x, %x, %x", float_to_int(my_old_v),
    //    float_to_int(north_elements[Z]), float_to_int(my_z),
    //    float_to_int(north_elements[CU]), float_to_int(my_cu),
    //    float_to_int(west_elements[CU]),
    //    float_to_int(north_west_elements[CU]), float_to_int(my_h),
    //    float_to_int(west_elements[H]));
}


//! \brief calculates the new u value based off other values
void calculate_new_u(float current_tdts_8, float current_tdtsdx){
    my_new_u = my_old_u + current_tdts_8 * (east_elements[Z] + my_z) *
        (east_elements[CV] + south_east_elements[CV] + south_elements[CV] +
         my_cv) - current_tdtsdx * (my_h - south_elements[H]);
}

//! \brief moves values from new to current sets
void transfer_data_from_new_to_current(){
    my_current_p = my_new_p;
    my_current_u = my_new_u;
    my_current_v = my_new_v;
}

//! \brief calculates the new u,v,p for this atom
void calculate_new_internal_states(bool if_first_time){
    float current_tdts_8;
    float current_tdtsdx;
    float current_tdtsdy;

    // deduce which constants to use (avoids a divide)
    if(if_first_time){
        current_tdts_8 = tdts8;
        current_tdtsdx = tdtsdx;
        current_tdtsdy = tdtsdy;
    }
    else{
        current_tdts_8 = tdt2s8;
        current_tdtsdx = tdt2sdx;
        current_tdtsdy = tdt2sdy;
    }

    // calculate the new states
    calculate_new_u(current_tdts_8, current_tdtsdx);
    calculate_new_v(current_tdts_8, current_tdtsdy);
    calculate_new_p(current_tdtsdx, current_tdtsdy);
}

//! \brief smooth old values for next cycle
void smooth_old_values(){
    my_old_u =
        my_current_u + alpha * (my_new_u - 2.0 * my_current_u + my_old_u);
    my_old_v =
        my_current_v + alpha * (my_new_v - 2.0 * my_current_v + my_old_v);
    my_old_p =
        my_current_p + alpha * (my_new_p - 2.0 * my_current_p + my_old_p);
}


//! \brief is the timer tick callback function. handles auto pause and resume,
//! as well as the reading of the input buffer, updating states and sending
//! new states to neighbours
void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    log_info("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {

        record_state();
        // Finalise any recordings that are in progress, writing back the final
        // amounts of samples recorded to SDRAM
        if (recording_flags > 0) {
            //log_info("updating recording regions");
            recording_finalise();
        }


        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        return;
    }

    //log_info("starting positional timer work");
    if (is_cv_or_p_calculation == CV_CU_Z_H){
        if (time > 0){
            read_input_buffer();
        }

        // calculate new parameters values
        calculate_cu();
        calculate_cv();
        calculate_z();
        calculate_h();

        send_cu_cv_h_z_states();
        is_cv_or_p_calculation = P_U_V;
    }
    else{
        read_input_buffer();

        // debug
        print_my_states();
        print_elements();

        calculate_new_internal_states(time == 0);

        // if first timer, no smoothing needed, just do transfer
        if (time == 0){
            transfer_data_from_new_to_current();
        }
        else{
            smooth_old_values();
            transfer_data_from_new_to_current();
        }

        // send new states to next core.
        send_p_u_v_states();
        //record_state();
        is_cv_or_p_calculation = CV_CU_Z_H;
    }
}


//! \brief this method is to catch strange behaviour
//! \param[in] key: the key being received
//! \param[in] unknown: second arg with no state. set to zero by default
void receive_data_void(uint key, uint unknown) {
    use(key);
    use(unknown);
    //log_error("this should never ever be done\n");
}


//! \brief sets my key from sdram
//! \param[in] address: the top level address location for dsg region data
void set_key(address_t address){
    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    has_key = transmission_region_address[HAS_KEY];
    if (has_key == TRUE) {
        my_key = transmission_region_address[MY_KEY];
        log_info("has key of value %d", my_key);
    }
}


//! \brief reads in the init states from sdram
//! \param[in] the address in sdram for the dsg region where this stuff starts
void set_init_states(address_t address){
    // read in the initial states
    // read my state
    address_t my_state_region_address = data_specification_get_region(
        INIT_STATE_VALUES, address);

    // converts sdram data into float data types for easier usage during
    // transfer to dtcm data items
    log_info("address of init data %08x", my_state_region_address);
    init_data_t *init_data =  (init_data_t*) my_state_region_address;

    // this cores initial states
    my_current_p = init_data->my_current_p;
    my_current_u = init_data->my_current_u;
    my_current_v = init_data->my_current_v;

    my_old_p = init_data->my_current_p;
    my_old_u = init_data->my_current_u;
    my_old_v = init_data->my_current_v;

    // north initial states
    north_elements[U] = init_data->north_u;
    north_elements[V] = init_data->north_v;
    north_elements[P] = init_data->north_p;

    // north east initial states
    north_east_elements[U] = init_data->north_east_u;
    north_east_elements[V] = init_data->north_east_v;
    north_east_elements[P] = init_data->north_east_p;

    // east initial states
    east_elements[U] = init_data->east_u;
    east_elements[V] = init_data->east_v;
    east_elements[P] = init_data->east_p;
    
    // south east initial states
    south_east_elements[U] = init_data->south_east_u;
    south_east_elements[V] = init_data->south_east_v;
    south_east_elements[P] = init_data->south_east_p;

    // south initial states
    south_elements[U] = init_data->south_u;
    south_elements[V] = init_data->south_v;
    south_elements[P] = init_data->south_p;

    // south west initial states
    south_west_elements[U] = init_data->south_west_u;
    south_west_elements[V] = init_data->south_west_v;
    south_west_elements[P] = init_data->south_west_p;

    // west initial states
    west_elements[U] = init_data->west_u;
    west_elements[V] = init_data->west_v;
    west_elements[P] = init_data->west_p;

    // north west initial states
    north_west_elements[U] = init_data->north_west_u;
    north_west_elements[V] = init_data->north_west_v;
    north_west_elements[P] = init_data->north_west_p;

    // get constants
    dx = init_data->dx;
    dy = init_data->dy;
    fsdx = init_data->fsdx;
    fsdy = init_data->fsdy;
    alpha = init_data->alpha;
    tdts8 = init_data->tdts8;
    tdtsdx = init_data->tdtsdx;
    tdtsdy = init_data->tdtsdy;
    tdt2s8 = init_data->tdt2s8;
    tdt2sdx = init_data->tdt2sdx;
    tdt2sdy = init_data->tdt2sdy;

    // print out the values
    print_my_states();
    print_elements();
    print_constants();
}


//! \brief reads in the keys expected from neighbours from sdram.
void set_neighbour_keys(address_t address){
    
    address_t my_neighbour_state_region_address =
        data_specification_get_region(NEIGHBOUR_KEYS, address);
    north_key = my_neighbour_state_region_address[NORTH];
    north_east_key = my_neighbour_state_region_address[NORTH_EAST];
    east_key = my_neighbour_state_region_address[EAST];
    south_east_key = my_neighbour_state_region_address[SOUTH_EAST];
    south_key = my_neighbour_state_region_address[SOUTH];
    south_west_key = my_neighbour_state_region_address[SOUTH_WEST];
    west_key = my_neighbour_state_region_address[WEST];
    north_west_key = my_neighbour_state_region_address[NORTH_WEST];
    key_mask = my_neighbour_state_region_address[KEY_MASK];

    log_info("north key = %d", north_key);
    log_info("north_east key = %d", north_east_key);
    log_info("east key = %d", east_key);
    log_info("south_east key = %d", south_east_key);
    log_info("south key = %d", south_key);
    log_info("south west key = %d", south_west_key);
    log_info("west key = %d", west_key);
    log_info("north_west key = %d", north_west_key);
    log_info("mask = %d", key_mask);

}


//! \brief reads in the timing details needed to enact the tdma agenda.
void set_timing_data(address_t address){
    address_t my_neighbour_state_region_address =
        data_specification_get_region(TIMING_DATA, address);
    window_offset = my_neighbour_state_region_address[TIME_OFFSET];
    time_between_spikes =
        my_neighbour_state_region_address[TIME_BETWEEN_PACKETS];
        log_info("my window offset is %d", window_offset);
        log_info("my time between spikes is %d", time_between_spikes);
}

//! \brief starts up the core, reading in all the init data from sdram.
//! \param[in] timer_period. the pointer for the timer period (set in sdram)
//! \param[out] bool which states if the init has been successful or not
static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started\n");

    // Get the address this core's DTCM data starts at from SDRAM
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
            &infinite_run, SDP)) {
        return false;
    }

    // set the provenance data area, and the exit function
    simulation_set_provenance_data_address(
        data_specification_get_region(PROVENANCE, address));
    simulation_set_exit_function(force_exit_function);

    // sort out recording interface
    address_t recording_region = data_specification_get_region(
        FINAL_STATES, address);
    bool success = recording_initialize(
        recording_region, &recording_flags);
    if (!success){
        return false;
    }
    log_info("Recording flags = 0x%08x", recording_flags);

    // find the key to use
    log_info("set key");
    set_key(address);

    // read in timing data
    log_info("set timing data");
    set_timing_data(address);

    // read in initials states
    log_info("set init states");
    set_init_states(address);

    // read in 

    // read neighbour keys
    log_info("set neighbour keys");
    set_neighbour_keys(address);

    // initialise my input_buffer for receiving packets
    log_info("build buffer");
    input_buffer = circular_buffer_initialize(512);
    if (input_buffer == 0){
        return false;
    }
    log_info("input_buffer initialised");

    return true;
}

//! \brief main entrance method. initialises this core and then sets up the
//! callbacks and event driven functions. Then finally calls run.
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
    log_info("setting multicast packet with payload receiver callback");
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    log_info("setting the timer tick callback");
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    // set state flag (switches between:
    // 0. calc cu, cv, z, h and sending cv, cu, h, z states
    // 1 calc new internal states, sending p, u, v, states and transfer data
    // between new and old
    is_cv_or_p_calculation = CV_CU_Z_H;

    // start sim
    simulation_run();
}
