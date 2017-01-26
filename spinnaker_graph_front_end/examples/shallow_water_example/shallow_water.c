
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

/*! buffer used to store spikes */
static circular_buffer input_buffer;
static uint32_t current_payload;
static uint32_t current_key;

static uint32_t N_PACKETS_PER_EDGE = 7;

//! The number of clock ticks to back off before starting the timer, in an
//! attempt to avoid overloading the network
static uint32_t random_backoff;

//! weather specific data items
s1615 my_current_p;
s1615 my_current_v;
s1615 my_current_u;
s1615 my_old_p;
s1615 my_old_v;
s1615 my_old_u;
s1615 my_new_p;
s1615 my_new_v;
s1615 my_new_u;
s1615 my_cv;
s1615 my_cu;
s1615 my_z;
s1615 my_h;

//! constants
s1615 dx;
s1615 dy;
s1615 fsdx;
s1615 fsdy;
s1615 alpha;
s1615 tdts8;
s1615 tdtsdx;
s1615 tdtsdy;
s1615 tdt2s8;
s1615 tdt2sdx;
s1615 tdt2sdy;

// weather receive data items
s1615 east_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 north_east_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 north_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 north_west_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 west_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 south_west_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 south_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};
s1615 south_east_elements[] = {0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

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
static const long unsigned fract POINT_5 = 0.5k;

// optimisation for doing multiplications in the logic code.
static const long unsigned fract POINT_025 = 0.25k;

// optimisation for doing divide in the logic code.
static const uint32_t EIGHT = 8.0k;

//! how many entries in the ring buffer that there should be per timer tick
static uint32_t N_PACKETS_PER_TIMER_TICK = 7 * 8 * 2;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION = 0,
    TRANSMISSIONS = 1,
    NEIGHBOUR_KEYS = 2,
    INIT_STATE_VALUES = 3,
    FINAL_STATES = 4
} regions_e;

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
    s1615 my_current_u; s1615 my_current_v; s1615 my_current_p;
    // neighbour values
    s1615 north_u; s1615 north_v; s1615 north_p;
    s1615 north_east_u; s1615 north_east_v; s1615 north_east_p;
    s1615 east_u; s1615 east_v; s1615 east_p;
    s1615 south_east_u; s1615 south_east_v; s1615 south_east_p;
    s1615 south_u; s1615 south_v; s1615 south_p;
    s1615 south_west_u; s1615 south_west_v; s1615 south_west_p;
    s1615 west_u; s1615 west_v; s1615 west_p;
    s1615 north_west_u; s1615 north_west_v; s1615 north_west_p;
    // constants
    uint32_t dx; uint32_t dy; s1615 fsdx; s1615 fsdy; 
    s1615 alpha; s1615 tdts8; s1615 tdtsdx; s1615 tdtsdy; s1615 tdt2s8;
    s1615 tdt2sdx; s1615 tdt2sdy;
    // offset fix
    uint32_t random_backoff;
}init_data_t;

//! human readable for the location in a array for element bits
typedef enum element_offsets {
    U = 0, V = 1, P = 2, Z = 3, H = 4, CV = 5, CU = 6
} element_offsets;

//! human readable for the location of keys in sdram
typedef enum key_order {
    NORTH = 0, NORTH_EAST = 1, EAST = 2, NORTH_WEST = 3, WEST = 4,
    SOUTH_WEST = 5, SOUTH = 6, SOUTH_EAST = 7
} key_order;

//! \brief print the constants of the vertex
void print_constants(){
    log_debug("doing constants");
    
    // create list of things to print
    s1615 to_print_items[] = {
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
    
    
    for(int position = 0; position < 6; position ++){
        log_debug(
            "%s = %k", to_print_strings[position], to_print_items[position]);
    }
    log_debug("end constants");
}

void force_exit_function()

//! \brief print my local states
void print_my_states(){
    s1615 to_print_items[] = {my_current_u, my_current_v, my_current_p};
    const char *to_print_strings[3];
    to_print_strings[0] = "my_current_u";
    to_print_strings[1] = "my_current_v";
    to_print_strings[2] = "my_current_p";
    for(int position = 0; position < 3; position++){
        log_debug(
            "%s = %k", to_print_strings[position], to_print_items[position]);
    }
    log_debug("my key = %d", my_key);
}

//! \brief print a set of elements for u,v,p
//! \param[in] elements_to_print: the array of elements to print elements of
//! \param[in] name: the name of the set of elements.
void print_a_set_of_elements(s1615 *elements_to_print, char* name){
    s1615 to_print_items[] = {elements_to_print[U], elements_to_print[V],
                             elements_to_print[P]};
    const char *to_print_strings[3];

    char copy_name[80];
    to_print_strings[0] = strcat(strcpy(copy_name, name), ":u");
    to_print_strings[1] = strcat(strcpy(copy_name, name), ":v");
    to_print_strings[2] = strcat(strcpy(copy_name, name), ":p");
    for(int position = 0; position < 3; position ++){
        log_debug(
            "%s = %k", to_print_strings[position], to_print_items[position]);
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
void process_key_payload(s1615 *elements, uint32_t *has_flag_elements){
    // get the offset in the array from the key
    uint32_t offset = current_key & 0x00000007;

    if (offset > 6){
        log_error("got wrong offset. The offset i got from key %d is %d",
        current_key, offset);
        rt_error(RTE_SWERR);
    }

    // add the element to the correct offset with a reinterpret cast to s1615
    elements[offset] = kbits(current_payload);
    has_flag_elements[offset] = 1;
}


//! \brief reads in the ring buffer to get all the packets needed for the run
void read_input_buffer(){

    uint32_t last_seen_size = 0;
    uint32_t current_buffer_size;
    while(circular_buffer_size(input_buffer) < N_PACKETS_PER_TIMER_TICK){
        current_buffer_size = circular_buffer_size(input_buffer);
        for(uint32_t counter=0; counter < 10000; counter++){
            //do nothing
        }

        if (current_buffer_size != last_seen_size){
            log_debug(
                "size of buffer is %d whereas it should be %d",
                current_buffer_size, N_PACKETS_PER_TIMER_TICK);
            last_seen_size = current_buffer_size;
        }
    }

    log_debug("running past buffer length");

    cpsr = spin1_int_disable();
    circular_buffer_print_buffer(input_buffer);

    // linked to the key offset map
    uint32_t has_east_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_north_east_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_north_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_north_west_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_west_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_south_west_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_south_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // linked to the key offset map
    uint32_t has_south_east_components[] = {
        0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k, 0.0k};

    // pull payloads and keys from input_buffer.
    // translate into s1615 elements
    for (uint32_t counter = 0; counter < N_PACKETS_PER_TIMER_TICK / 2;
            counter ++){
        bool success1 = circular_buffer_get_next(
            input_buffer, &current_payload);
        bool success2 = circular_buffer_get_next(
            input_buffer, &current_key);
        if (success1 && success2){

            // deduce what the base key is
            uint32_t key_mask = 0xFFFFFFF0;
            uint32_t masked_key = current_key & key_mask;

            // process into the correct location
            if (masked_key == north_key){
                process_key_payload(
                    north_elements, has_north_components);
            }
            else if (masked_key == north_east_key){
                process_key_payload(
                    north_east_elements, has_north_east_components);
            }
            else if (masked_key == east_key){
                process_key_payload(east_elements, has_east_components);
            }
            else if (masked_key == south_east_key){
                process_key_payload(
                    south_east_elements, has_south_east_components);
            }
            else if (masked_key == south_key){
                process_key_payload(south_elements, has_south_components);
            }
            else if (masked_key == south_west_key){
                process_key_payload(
                    south_west_elements, has_south_west_components);
            }
            else if (masked_key == north_west_key){
                process_key_payload(
                    north_west_elements, has_north_west_components);
            }
            else if (masked_key == west_key){
                process_key_payload(west_elements, has_west_components);
            }
        }
        else{
            log_debug("couldn't read state from my neighbours.");
        }
    }
    spin1_mode_restore(cpsr);
}

//! \brief records the data into the recording region
void record_state(){
    // record my state via sdram
    recording_record(0, &my_current_p, 4);
    recording_record(0, &my_current_u, 4);
    recording_record(0, &my_current_v, 4);
    recording_record(0, &my_cu, 4);
    recording_record(0, &my_cv, 4);
    recording_record(0, &my_z, 4);
    recording_record(0, &my_h, 4);
    recording_do_timestep_update(time);
    log_debug("recorded my state \n");
}

//! \brief sends the states needed for the neighbours to do their calculation.
void send_states(){
    // send my new state to the simulation neighbours
    uint32_t elements_to_send[7] =
        {my_current_u, my_current_v, my_current_p, my_z, my_h, my_cv, my_cu};

    const char *to_print_strings[7];
    to_print_strings[0] = "my_current_u";
    to_print_strings[1] = "my_current_v";
    to_print_strings[2] = "my_current_p";
    to_print_strings[3] = "my_z";
    to_print_strings[4] = "my_h";
    to_print_strings[5] = "my_cv";
    to_print_strings[6] = "my_cu";

    for(uint32_t position = 0; position < N_PACKETS_PER_EDGE; position++){
        // log what we're firing
        uint32_t this_data_key = my_key + position;
        log_debug(
            "firing packet %s with value %d with key %d",
            to_print_strings[position], elements_to_send[position],
            this_data_key);

        while (!spin1_send_mc_packet(
                this_data_key, (uint) elements_to_send[position],
                WITH_PAYLOAD)) {
            spin1_delay_us(1);
        }
    }
    log_debug("sent my states via multicast");
}


//! \brief calculates the cu for this atom
void calculate_cu(){
    my_cu = POINT_5 * (my_current_p + south_elements[P]) * my_current_u;
}

//! \brief calculates the cv for this atom
void calculate_cv(){
    my_cv = POINT_5 * (my_current_p + west_elements[P] * my_current_v);
}

//! \brief calculates the z for this atom
void calculate_z(){
    s1615 numerator_bit =
        (fsdx * (my_current_v - south_elements[V]) - fsdy *
        (my_current_u - west_elements[U]));
    s1615 denominator_bit =
        (south_west_elements[P] + west_elements[P] + my_current_p +
         south_elements[P]);
    my_z = numerator_bit / denominator_bit;
}

//! \brief calculates the h for this atom
void calculate_h(){
    my_h = my_current_p + POINT_025 * (
        north_elements[U] * north_elements[U] + my_current_u * my_current_u +
        east_elements[V] * my_current_v * my_current_v);
}

//! \brief calculates the new p value based off other values
void calculate_new_p(s1615 current_tdtsdx, s1615 current_tdtsdy){
    my_new_p = my_old_p - current_tdtsdx * (north_elements[CU] - my_cu) -
        current_tdtsdy * (east_elements[CV] - my_cv);
}


//! \brief calculates the new v value based off other values
void calculate_new_v(s1615 current_tdts_8, s1615 current_tdtsdy){
    my_new_v = my_old_v - current_tdts_8 *(north_elements[Z] + my_z) *
        (north_elements[CU] + my_cu + west_elements[CU] +
        south_west_elements[CU]) - current_tdtsdy * (my_h - south_elements[H]);
}


//! \brief calculates the new u value based off other values
void calculate_new_u(s1615 current_tdts_8, s1615 current_tdtsdx){
    my_new_u = my_old_u + current_tdts_8 * (east_elements[Z] + my_z) *
        (east_elements[CV] + south_west_elements[CV] + south_elements[CV] +
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
    s1615 current_tdts_8;
    s1615 current_tdtsdx;
    s1615 current_tdtsdy;

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

    log_debug("setting off random back off");
    // Wait a random number of clock cycles to smooth out comms traffic
    uint32_t random_backoff_time = tc[T1_COUNT] - random_backoff;
    while (tc[T1_COUNT] > random_backoff_time) {
        // Do Nothing
    }
    log_debug("finished random back off");

    time++;

    log_debug("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {

        record_state();
        // Finalise any recordings that are in progress, writing back the final
        // amounts of samples recorded to SDRAM
        if (recording_flags > 0) {
            log_debug("updating recording regions");
            recording_finalise();
        }


        log_debug("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        return;
    }

    if (time > 0){
        read_input_buffer();
    }

    // calculate new parameters values
    calculate_cu();
    calculate_cv();
    calculate_z();
    calculate_h();

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


//! \brief sets my key from sdram
//! \param[in] address: the top level address location for dsg region data
void set_key(address_t address){
    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    has_key = transmission_region_address[HAS_KEY];
    if (has_key == TRUE) {
        my_key = transmission_region_address[MY_KEY];
        log_debug("has key of value %d", my_key);
    }
}

//! \brief reads in the init states from sdram
//! \param[in] the address in sdram for the dsg region where this stuff starts
void set_init_states(address_t address){
    // read in the initial states
    // read my state
    address_t my_state_region_address = data_specification_get_region(
        INIT_STATE_VALUES, address);

    // converts sdram data into s1615 data types for easier usage during
    // transfer to dtcm data items
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

    // get random backoff
    random_backoff = init_data->random_backoff;

    // print out the values
    print_my_states();
    print_elements();
    print_constants();
}


//! \brief reads in the keys expected from neighbours from sdram.
void set_neighbour_keys(address_t address){
    
    address_t my_neighbour_state_region_address =
        data_specification_get_region(NEIGHBOUR_KEYS, address);
    north_key = my_neighbour_state_region_address[SOUTH];
    north_east_key = my_neighbour_state_region_address[SOUTH_WEST];
    east_key = my_neighbour_state_region_address[WEST];
    south_east_key = my_neighbour_state_region_address[SOUTH_EAST];
    south_key = my_neighbour_state_region_address[SOUTH];
    south_west_key = my_neighbour_state_region_address[SOUTH_WEST];
    west_key = my_neighbour_state_region_address[WEST];
    north_west_key = my_neighbour_state_region_address[NORTH_WEST];
}

//! \brief starts up the core, reading in all the init data from sdram.
//! \param[in] timer_period. the pointer for the timer period (set in sdram)
//! \param[out] bool which states if the init has been successful or not
static bool initialize(uint32_t *timer_period) {
    log_debug("Initialise: started\n");

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
            &infinite_run, SDP, NULL, NULL)) {
        return false;
    }

    // sort out recording interface
    address_t recording_region = data_specification_get_region(
        FINAL_STATES, address);
    bool success = recording_initialize(
        recording_region, &recording_flags);
    if (!success){
        return false;
    }
    log_debug("Recording flags = 0x%08x", recording_flags);

    // find the key to use
    log_debug("set key");
    set_key(address);

    // read in initials states
    log_debug("set init states");
    set_init_states(address);

    // read in 

    // read neighbour keys
    log_debug("set neighbour keys");
    set_neighbour_keys(address);

    // initialise my input_buffer for receiving packets
    log_debug("build buffer");
    input_buffer = circular_buffer_initialize(512);
    if (input_buffer == 0){
        return false;
    }
    log_debug("input_buffer initialised");

    return true;
}

//! \brief main entrance method. initialises this core and then sets up the
//! callbacks and event driven functions. Then finally calls run.
void c_main() {
    log_debug("starting weather cell\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        log_error("Error in initialisation - exiting!");
        rt_error(RTE_SWERR);
    }

    // set timer tick value to configured value
    log_debug("setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    log_debug("setting multicast packet with payload receiver callback");
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    log_debug("setting the timer tick callback");
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_debug("Starting\n");
    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
