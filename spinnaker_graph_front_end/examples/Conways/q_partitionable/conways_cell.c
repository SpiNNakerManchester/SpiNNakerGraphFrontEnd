
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include "conways_cell.h"
#include "packet_processing.c"
#include "population_table/population_table.h"
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

//! Array of cell states
static synapse_param_t *cell_array;

//! neighbour states for next iteration
uint32_t *alive_states_received_this_tick;
uint32_t *dead_states_received_this_tick;

//! recorded data items
uint32_t size_written = 0;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
uint32_t time = 0;
address_t address = NULL;

//! The recording flags
static uint32_t recording_flags = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

// value for turning on and off interrupts
uint cpsr = 0;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION = 0,
    TRANSMISSIONS = 1,
    SYNAPSE_PARAMS_REGION = 2,
    POPULATION_TABLE_REGION = 3,
    SYNAPTIC_MATRIX_REGION = 4,
    STATE = 5,
    NEIGHBOUR_INITIAL_STATES = 6,
    RECORDED_DATA = 7,
    RECORDING_STATE_REGION = 8
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC = -1, SDP_AND_DMA_AND_USER= 0, TIMER = 2
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

    log_debug("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {

        log_debug("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        // Finalise any recordings that are in progress, writing back the final
        // amounts of samples recorded to SDRAM
        if (recording_flags > 0) {
            log_debug("updating recording regions");
            recording_finalise();
        }

        return;
    }

    if(time ==0){
        for (uint32_t cell=0; cell < n_cells; cell++){
            // record the new state for the host
            recording_record(0, &cell_array[cell].state, 4);
        }
    }

    for (uint32_t cell=0; cell < n_cells; cell++){
        // find the cell's next state
        next_state(cell);

        // send the cell's state to its neighbours
        send_state(cell);

        if (time == 0){
            log_info(
                "Send cell %d's first state %d!", cell, cell_array[cell].state);
        }
        else{
            log_info(
                "Send cell %d's state %d!", cell, cell_array[cell].state);
        }

        // record the new state for the host
        recording_record(0, &cell_array[cell].state, 4);
    }
}

void do_safety_check(uint32_t cell_id){
    // do a safety check on number of states. Not like we can fix it
    // if we've missed events
    cpsr = spin1_int_disable();
    int total = alive_states_received_this_tick[cell_id] +
        dead_states_received_this_tick[cell_id];
    if (total != 8){
         log_error("didn't receive the correct number of states");
         log_error("only received %d states", total);
    }
    log_debug("only received %d alive states",
             alive_states_received_this_tick[cell_id]);
    log_debug("only received %d dead states",
             dead_states_received_this_tick[cell_id]);
    spin1_mode_restore(cpsr);
}

bool read_cell_row(uint32_t n_time, synaptic_row_t row, uint32_t payload,
                       uint32_t process_id){
    use(n_time);
    use(process_id);

    log_debug("residing in read cell row");

    uint32_t n_cells_affected = ((size_t) (row[1]));

    log_debug("am dealing with %d cells to affect from this row", n_cells_affected);
    for (uint32_t affected_cell =0; affected_cell < n_cells_affected;
         affected_cell++){
        uint32_t cell_id =  row[affected_cell + 2]& 0xFF;
        log_debug("dealing with cell %d", affected_cell);
        if (payload == ALIVE){
            alive_states_received_this_tick[cell_id] ++;
            log_debug("adding to alive states for cell %d", cell_id);
        }
        else{
            dead_states_received_this_tick[cell_id] ++;
            log_debug("adding to dead states for cell %d", cell_id);
        }
    }
    log_debug("finished rows");
    return true;
}

void send_state(uint32_t cell_id){
    // reset for next iteration
    alive_states_received_this_tick[cell_id] = 0;
    dead_states_received_this_tick[cell_id] = 0;

    // send my new state to the simulation neighbours
    log_debug("sending cell %d state of %d via multicast with key %d",
              cell_id, cell_array[cell_id], my_base_key + cell_id);
    while (!spin1_send_mc_packet(
            my_base_key + cell_id, cell_array[cell_id].state, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

    log_debug("sent cell %d state via multicast", cell_id);
}

void next_state(uint32_t cell_id){

    // calculate new state from the total received so far
    if (cell_array[cell_id].state == ALIVE){
        if(alive_states_received_this_tick[cell_id] <= 1){
            cell_array[cell_id].state = DEAD;
            log_debug("changing cell %d to state DEAD", cell_id);
        }
        if ((alive_states_received_this_tick[cell_id] == 2) ||
                (alive_states_received_this_tick[cell_id] == 3)){
            cell_array[cell_id].state = ALIVE;
            log_debug("changing cell %d to state ALIVE", cell_id);
        }
        if (alive_states_received_this_tick[cell_id] >= 4){
            cell_array[cell_id].state = DEAD;
            log_debug("changing cell %d to state DEAD", cell_id);
        }
    }
    else if (alive_states_received_this_tick[cell_id] == 3){
        cell_array[cell_id].state = ALIVE;
        log_debug("changing cell %d to state ALIVE", cell_id);
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
    log_debug("Recording flags = 0x%08x", recording_flags);
    return success;
}

void print_states(){
    for(uint32_t cell_id=0; cell_id < n_cells; cell_id++){
        log_debug("cell %d has state %d", cell_id, cell_array[cell_id]);
    }
}

static bool initialize(uint32_t *timer_period) {
    log_debug("Initialise: started\n");

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
        log_debug("my key is %d\n", my_base_key);
        log_debug("i'm simulating %d cells\n", n_cells);
    } else {
        log_error(
            "this conways cell can't effect anything, deduced as an error,"
            "please fix the application fabric and try again\n");
        return false;
    }

    // create arrays for neighbours of each cell within this core.
    alive_states_received_this_tick =
        sark_alloc(n_cells, sizeof(uint32_t));
    dead_states_received_this_tick =
        sark_alloc(n_cells, sizeof(uint32_t));
    log_debug("allocated the two sets of state trackers.\n");

    // read neighbour states for initial tick
    address_t my_neighbour_state_region_address =
        data_specification_get_region(NEIGHBOUR_INITIAL_STATES, address);

    // read the alive stuff
    uint32_t position = 0;
    for (uint32_t cell_id = 0; cell_id < n_cells; cell_id++){
        alive_states_received_this_tick[cell_id] =
            my_neighbour_state_region_address[position];
        log_debug("alive niegbouring states for cell %d are %d", cell_id, my_neighbour_state_region_address[position]);
        position += 1;
    }

    // read the dead stuff
    for (uint32_t cell_id = 0; cell_id < n_cells; cell_id++){
        dead_states_received_this_tick[cell_id] =
            my_neighbour_state_region_address[position];
        log_debug("dead niegbouring states for cell %d are %d", cell_id, my_neighbour_state_region_address[position]);
        position += 1;
    }
    log_debug("written the blocks of data for the initial iteration");

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(8 * 2 * n_cells);
    log_debug("created the input buffer");

    if (input_buffer == 0){
        log_debug("failed to allocate input buffer");
        return false;
    }
    log_debug("input_buffer initialised");

    // set up buffered recording region
    if (!initialise_recording()){
        return false;
    }

    // Allocate block of memory for this synapse type'synapse_index
    // pre-calculated per-neuron decay
    cell_array = (synapse_param_t *) spin1_malloc(
            (sizeof(synapse_param_t) * n_cells));
    log_debug("allocated %d bytes for the synpase params",
             sizeof(synapse_param_t) * n_cells);

    // Check for success
    if (cell_array == NULL) {
        log_error("Cannot allocate cell parameters - Out of DTCM");
        return false;
    }

    // grab the cell data from the original synapse type location
    address_t cell_data_address =
        data_specification_get_region(SYNAPSE_PARAMS_REGION, address);
    log_debug(
        "\tCopying %u bytes from %u", n_cells * sizeof(synapse_param_t),
        cell_data_address + ((n_cells * sizeof(synapse_param_t)) / 4));
    memcpy(cell_array, cell_data_address, (n_cells * sizeof(synapse_param_t)));

    print_states();

    // Work out the positions of the direct and indirect synaptic matrices
    // and copy the direct matrix to DTCM
    address_t synaptic_matrix_address =
        data_specification_get_region(SYNAPTIC_MATRIX_REGION, address);
    uint32_t direct_matrix_offset = (synaptic_matrix_address[0] >> 2) + 1;
    log_debug("Indirect matrix is %u words in size", direct_matrix_offset - 1);
    uint32_t direct_matrix_size = synaptic_matrix_address[direct_matrix_offset];
    log_debug("Direct matrix malloc size is %d", direct_matrix_size);
    address_t direct_synapses_address = NULL;

    // if there is a direct matrix, read it in
    if (direct_matrix_size != 0) {
        address_t direct_synapses_address =
            (address_t) spin1_malloc(direct_matrix_size);
        if (direct_synapses_address == NULL) {
            log_error("Not enough memory to allocate direct matrix");
            return false;
        }
        log_debug(
            "Copying %u bytes of direct synapses to 0x%08x",
            direct_matrix_size, *direct_synapses_address);
        spin1_memcpy(
            *direct_synapses_address,
            &(synaptic_matrix_address[direct_matrix_offset + 1]),
            direct_matrix_size);
    }
    address_t indirect_synapses_address = &(synaptic_matrix_address[1]);

    // Set up the population table
    uint32_t row_max_n_words;
    if (!population_table_initialise(
            data_specification_get_region(POPULATION_TABLE_REGION, address),
            indirect_synapses_address, direct_synapses_address,
            &row_max_n_words)) {
        return false;
    }

    // build the system for receiving packets and placing them into the correct
    // buffer
    if (!packet_processing_initialise(
            row_max_n_words, MC, SDP_AND_DMA_AND_USER, SDP_AND_DMA_AND_USER,
            input_buffer, read_cell_row)) {
        return false;
    }
    log_debug("Initialise: finished");

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
    log_debug("starting conway_cell\n");

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
    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_debug("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
