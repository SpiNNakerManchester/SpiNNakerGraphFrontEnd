
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include "conways_cell.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>

/*! multicast routing keys to communicate with neighbours */
static uint32_t my_base_key;

/*! the number of cells being simulated on this core */
static uint32_t n_cells = 0;

/*! buffer used to store spikes */
static circular_buffer input_buffer;
static uint32_t current_payload;

//! Array of cell states
static neuron_pointer_t cell_array;

//! neighbour states for next iteration
uint32_t *alive_states_recieved_this_tick;
uint32_t *dead_states_recieved_this_tick;

//! recorded data items
uint32_t size_written = 0;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t time = 0;
address_t address = NULL;

//! The recording flags
static uint32_t recording_flags = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

// value for turning on and off interrupts
uint cpsr = 0;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    TRANSMISSIONS,
    STATE,
    NEIGHBOUR_INITIAL_STATES,
    RECORDED_DATA,
    RECORDING_STATE_REGION
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, TIMER = 2
} callback_priorities;

//! values for the states
typedef enum states_values{
    ALIVE = 1, DEAD = 0
} states_values;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_BASE_KEY, N_CELLS
} transmission_region_elements;

//! human readable definitions of each element in the initial state
//! region
typedef enum initial_state_region_elements {
    INITIAL_STATE
} initial_state_region_elements;


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
    if (!circular_buffer_add(input_buffer, key)) {
        log_info("Could not add key");
    }
    if (!circular_buffer_add(input_buffer, payload)) {
        log_info("Could not add payload");
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

        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        // Finalise any recordings that are in progress, writing back the final
        // amounts of samples recorded to SDRAM
        if (recording_flags > 0) {
            log_info("updating recording regions");
            recording_finalise();
        }

        return;
    }

    if (time == 0){
        for (uint32_t cell=0; cell < n_cells; cell++){
            // find the cell's next state
            next_state(cell);

            // send the cell's state to its neighbours
            send_state(cell);

            // record the new state for the host
            recording_record(0, &cell_array[cell], 4);
            log_debug(
                "Send cell %d's first state %d!", cell, &cell_array[cell]);
        }
    }
    else{

        // translate recieved packets into the neighbouring states array
        read_input_buffer();

        for (uint32_t cell=0; cell < n_cells; cell++){
            // find my next state
            next_state(cell);

            // do a safety check on number of states. Not like we can fix it
            // if we've missed events
            do_safety_check(cell);

            // send the cell's state to its neighbours
            send_state(cell);
            log_debug(
                "Send cell %d's first state %d!", cell, &cell_array[cell]);

            // record the new state for the host
            recording_record(0, &cell_array[cell], 4);
            recording_do_timestep_update(time);
        }
    }
}

void do_safety_check(uint32_t cell_id){
    // do a safety check on number of states. Not like we can fix it
    // if we've missed events
    cpsr = spin1_int_disable();
    int total = alive_states_recieved_this_tick[cell_id] +
        dead_states_recieved_this_tick[cell_id];
    if (total != 8){
         log_error("didn't receive the correct number of states");
         log_error("only received %d states", total);
    }
    log_debug("only received %d alive states",
             alive_states_recieved_this_tick[cell_id]);
    log_debug("only received %d dead states",
             dead_states_recieved_this_tick[cell_id]);
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

void send_state(uint32_t cell_id){
    // reset for next iteration
    alive_states_recieved_this_tick[cell_id] = 0;
    dead_states_recieved_this_tick[cell_id] = 0;

    // send my new state to the simulation neighbours
    log_debug("sending cell %d state of %d via multicast with key %d",
              cell_id, cell_array[cell_id], my_base_key + cell_id);
    while (!spin1_send_mc_packet(
            my_base_key + cell_id, cell_array[cell_id], WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

    log_debug("sent cell %d state via multicast", cell_id);
}

void next_state(uint32_t cell_id){

    // calculate new state from the total received so far
    if (cell_array[cell_id].state == ALIVE){
        if(alive_states_recieved_this_tick[cell_id] <= 1){
            cell_array[cell_id].state = DEAD;
        }
        if ((alive_states_recieved_this_tick[cell_id] == 2) ||
                (alive_states_recieved_this_tick[cell_id] == 3)){
            cell_array[cell_id].state = ALIVE;
        }
        if (alive_states_recieved_this_tick[cell_id] >= 4){
            cell_array[cell_id].state = DEAD;
        }
    }
    else if (alive_states_recieved_this_tick[cell_id] == 3){
        cell_array[cell_id].state = ALIVE;
    }
}

//! \brief this method is to catch strange behaviour
//! \param[in] key: the key being received
//! \param[in] unknown: second arg with no state. set to zero by default
void receive_data_void(uint key, uint unknown) {
    use(key);
    use(unknown);
    log_error("this should never ever be done\n");
}

static bool initialise_recording(){
    address_t address = data_specification_get_data_address();
    address_t system_region = data_specification_get_region(
        SYSTEM_REGION, address);
    regions_e regions_to_record[] = {
        RECORDED_DATA
    };
    uint8_t n_regions_to_record = 1;
    uint32_t *recording_flags_from_system_conf =
        &system_region[SIMULATION_N_TIMING_DETAIL_WORDS];
    regions_e state_region = RECORDING_STATE_REGION;

    bool success = recording_initialize(
        n_regions_to_record, regions_to_record,
        recording_flags_from_system_conf, state_region, &recording_flags);
    log_info("Recording flags = 0x%08x", recording_flags);
    return success;
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
        my_base_key = transmission_region_address[MY_BASE_KEY];
        n_cells = transmission_region_address[N_CELLS];
        log_info("my key is %d\n", my_base_key);
        log_info("i'm simulating %d cells\n", n_cells);
    } else {
        log_error(
            "this conways cell can't effect anything, deduced as an error,"
            "please fix the application fabric and try again\n");
        return false;
    }

    // read neighbour states for initial tick
    address_t my_neigbhour_state_region_address =
        data_specification_get_region(NEIGHBOUR_INITIAL_STATES, address);

    // create arrays for neigbuours of each cell within this core.
    alive_states_recieved_this_tick =
        sark_alloc(n_cells, sizeof(uint32_t));
    dead_states_recieved_this_tick =
        sark_alloc(n_cells, sizeof(uint32_t));

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(8 * 2 * n_cells);

    if (input_buffer == 0){
        return false;
    }
    log_info("input_buffer initialised");

    // set up buffered recording region
    if (!initialise_recording()){
        return false;
    }

    // setup edge manager
    // Allocate DTCM for neuron array and copy block of data
    if (sizeof(neuron_t) != 0) {
        cell_array = (neuron_t *) spin1_malloc(n_cells * sizeof(neuron_t));
        if (cell_array == NULL) {
            log_error("Unable to allocate cell array - Out of DTCM");
            return false;
        }
        memcpy(cell_array, &address[next], n_cells * sizeof(neuron_t));
    }

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
    log_info("starting conway_cell\n");

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
