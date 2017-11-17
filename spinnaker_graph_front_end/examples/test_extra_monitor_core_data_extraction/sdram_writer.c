
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

//! convert between words to bytes
#define WORD_TO_BYTE_MULTIPLIER 4

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! state for how many bytes it needs to send, gives approx bandwidth if 
//! round number. 
static uint32_t bytes_to_write;
static address_t *store_address = NULL;
address_t dsg_main_address;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION, CONFIG, DATA_REGION
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
   SDP = 0, DMA = 0, TIMER = 2
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum config_region_elements {
    MB
} config_region_elements;


//! boiler plate: not really needed
void resume_callback() {
    time = UINT32_MAX;
}

//! method to make test data in sdram
void write_data(){
    // write data into sdram for reading later
    address_t address = data_specification_get_data_address();
    store_address = data_specification_get_region(DATA_REGION, address);

    uint iterations = (uint)(bytes_to_write / WORD_TO_BYTE_MULTIPLIER);
    //log_info("iterations = %d", iterations - 1);

    for(uint count = 0; count < iterations; count++){
        store_address[count] = count;
    }
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

    // read config params.
    address_t config_address = data_specification_get_region(CONFIG, address);
    bytes_to_write = config_address[MB];

    log_info("bytes to write is %d", bytes_to_write);

    return true;
}

void update(uint ticks, uint b) {
    use(b);
    use(ticks);

    time++;

    log_info("on tick %d of %d", time, simulation_ticks);

    // check that the run time hasn't already elapsed and thus needs to be
    // killed
    if ((infinite_run != TRUE) && (time >= simulation_ticks)) {

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        return;
    }
}

void c_main() {

    uint32_t timer_period;
    log_info("starting sdram reader and writer\n");

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    // write data
    write_data();
    spin1_set_timer_tick(timer_period);

    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
