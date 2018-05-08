
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;
static uint32_t count = 0;
static uint32_t size = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION, LARGE_DATA, SIZE_OF_LARGE_DATA
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
   TIMER = 2, SDP = 0, DMA = 0
} callback_priorities;

//! human readable definitions of each element in the size region
typedef enum config_region_elements {
    ITERATIONS
} config_region_elements;


//! boiler plate: not really needed
void resume_callback() {
    time = UINT32_MAX;
    log_info("was up to count %d out of %d\n", count, size);
}

//! method to make test data in sdram
void read_data(){
    // write data into sdram for reading later
    address_t address = data_specification_get_data_address();
    address_t store_address =
        data_specification_get_region(SIZE_OF_LARGE_DATA, address);
    size = store_address[ITERATIONS];
    address_t data = data_specification_get_region(LARGE_DATA, address);
    log_info("was looking in address %u", data);

    for(count = 0; count < size; count++){
        if (data[count] != count){
            log_error("was looking for value %u, found %u. stopping",
                      count, data[count]);
            rt_error(RTE_SWERR);
        }
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

        read_data();
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

    spin1_set_timer_tick(timer_period);

    spin1_callback_on(TIMER_TICK, update, TIMER);

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
