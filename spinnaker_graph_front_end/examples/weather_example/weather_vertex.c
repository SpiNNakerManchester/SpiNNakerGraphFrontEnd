
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>

/*! multicast routing keys to communicate with neighbours */
uint my_key;

/*! buffer used to store spikes */
static circular_buffer input_buffer;
static uint32_t current_payload;

//! Conways specific data items
uint32_t my_state = 0;
int alive_states_recieved_this_tick = 0;
int dead_states_recieved_this_tick = 0;

//! recorded data items
uint32_t size_written = 0;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t time = 0;
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

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;

//! human readable definitions of each element in the initial state
//! region
typedef enum initial_state_region_elements {
    U_INIT = 0, V_INIT = 2, P_INIT = 4, PSI_INIT = 6,
    AT_EAST_EDGE = 7,
        EAST_HARD_CODED_U = 8,
        EAST_HARD_CODED_V = 10,
        EAST_HARD_CODED_P = 12,
    AT_NORTH_EAST_EDGE = 14,
        NORTH_EAST_HARD_CODED_U = 15,
        NORTH_EAST_HARD_CODED_V = 17,
        NORTH_EAST_HARD_CODED_P = 19,
    AT_NORTH_EDGE = 21,
        NORTH_HARD_CODED_U = 22,
        NORTH_HARD_CODED_V = 24,
        NORTH_HARD_CODED_P = 26,
    TDT = 28, DX = 30, DY = 32, FSDX = 34, FSDY = 36, ALPHA = 38
} initial_state_region_elements;

//! human readable for the key allocation



/****f* conways.c/receive_data
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
    // If there was space to add spike to incoming spike queue
    if (!circular_buffer_add(input_buffer, payload)) {
        log_info("Could not add state");
    }
}

/****f* conways.c/update
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
            data_specification_get_region(RECORDED_DATA, address);
        uint8_t* record_space_address = (uint8_t*) record_region;
        log_info("wrote final store of %d bytes", size_written);
        spin1_memcpy(record_space_address, &size_written, 4);

        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        return;
    }

    if (time == 0){
        next_state();
        send_state();
        record_state();
        log_info("Send my first state!");
    }
    else{

        read_input_buffer();

        // find my next state
        next_state();

        // do a safety check on number of states. Not like we can fix it
        // if we've missed events
        do_safety_check();

        send_state();

        record_state();
    }
}

void do_safety_check(){
    // do a safety check on number of states. Not like we can fix it
    // if we've missed events
    cpsr = spin1_int_disable();
    int total = alive_states_recieved_this_tick +
        dead_states_recieved_this_tick;
    if (total != 8){
         log_error("didn't receive the correct number of states");
         log_error("only received %d states", total);
    }
    log_debug("only received %d alive states",
             alive_states_recieved_this_tick);
    log_debug("only received %d dead states",
             dead_states_recieved_this_tick);
    spin1_mode_restore(cpsr);
}

void read_input_buffer(){

    cpsr = spin1_int_disable();
    circular_buffer_print_buffer(input_buffer);
    // pull payloads from input_buffer. Filter for alive and dead states
    for (uint32_t counter = 0; counter < 8;
             counter ++){
        bool success = circular_buffer_get_next(input_buffer, &current_payload);
        if (success){
            if (current_payload == DEAD){
                 dead_states_recieved_this_tick += 1;
            }
            else if(current_payload == ALIVE){
                 alive_states_recieved_this_tick += 1;
            }
            else{
                 log_error("Not recognised payload");
            }
        }
        else{
            log_debug("couldn't read state from my neighbours.");
        }

    }
    spin1_mode_restore(cpsr);
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

//! \brief this method is to catch strange behaviour
//! \param[in] key: the key being received
//! \param[in] unknown: second arg with no state. set to zero by default
void receive_data_void(uint key, uint unknown) {
    use(key);
    use(unknown);
    log_error("this should never ever be done\n");
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

    // initialise transmission keys
    address_t transmission_region_address = data_specification_get_region(
            TRANSMISSIONS, address);
    if (transmission_region_address[HAS_KEY] == 1) {
        my_key = transmission_region_address[MY_KEY];
        log_info("my key is %d\n", my_key);
    } else {
        log_error(
            "this weather cell can't effect anything, deduced as an error,"
            "please fix the application fabric and try again\n");
        return false;
    }

    // read my state
    address_t my_state_region_address = data_specification_get_region(
        STATE, address);
        ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    my_state = my_state_region_address[INITIAL_STATE];
    log_info("my initial state is %d\n", my_state);

    // read neighbour states for initial tick
    address_t my_neigbhour_state_region_address = data_specification_get_region(
        NEIGHBOUR_INITIAL_STATES, address);
    alive_states_recieved_this_tick = my_neigbhour_state_region_address[0];
    dead_states_recieved_this_tick = my_neigbhour_state_region_address[1];

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(256);
    if (input_buffer == 0){
        return false;
    }
    log_info("input_buffer initialised");

    return true;


}

/****f* conways.c/c_main
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
