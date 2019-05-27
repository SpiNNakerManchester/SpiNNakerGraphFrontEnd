
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <recording.h>
#include <simulation.h>
#include <debug.h>
#include <circular_buffer.h>

int value_a;
int value_b;
int counter = 0;
int result = 0;

uint my_key;
// KA : set parameters that will be used in the receive data method
static circular_buffer input_buffer;
// KA : Transmitted flag
uint32_t flag = 0;

static uint32_t time = 0;

// value for turning on and off interrupts
uint cpsr = 0;

//! The recording flags
static uint32_t recording_flags = 0;

typedef enum regions_e {
    INPUT_CONST_VALUES,
    RECORDED_DATA
} regions_e;


typedef enum callback_priorities{
    MC_PACKET = -1, USER = 3
} callback_priorities;


void record_data(int result) {
    log_debug("Recording data\n");

    log_debug("Result %d",result);
    uint chip = spin1_get_chip_id();

    uint core = spin1_get_core_id();

    log_debug("Issuing 'Result' from chip %d, core %d", chip, core);

    bool recorded = recording_record(0, &result, 4);

    if (recorded) {
        log_debug("Result recorded successfully!");
    } else {
        log_error("Result was not recorded...");
    }
}

int addition(int a, int b){
    log_info("addition\n");
    int total;
    log_info("Addition of A %d and B %d \n", a , b);
    total = a + b;
    return total;
}


void receive_data(uint key, uint payload) {
    log_info("receive_data\n");
    log_info("the key i've received is %d\n", key);
    log_info("the payload i've received is %d\n", payload);
    counter +=1;
    if(counter == 1){
        value_a = payload;
    }
    else{
        value_b = payload;
        result = addition(value_a, value_b);
        record_data(result);
    }

    if (!circular_buffer_add(input_buffer, payload)) {
        log_info("Could not add state");
    }
}



//! \brief Initialises the recording parts of the model
//! \return True if recording initialisation is successful, false otherwise
static bool initialise_recording(){
    log_info("initialise_recording\n");
    address_t address = data_specification_get_data_address();
    address_t recording_region = data_specification_get_region(
        RECORDED_DATA, address);

    bool success = recording_initialize(recording_region, &recording_flags);
    log_info("Recording flags = 0x%08x", recording_flags);
    return success;
}

void resume_callback() {
    time = UINT32_MAX;
}

void read_input_buffer(){
    log_debug("read_input_buffer");

    cpsr = spin1_int_disable();
    circular_buffer_print_buffer(input_buffer);

    spin1_mode_restore(cpsr);
}


static bool initialize() {
    log_info("Initialise addition: started\n");

    // Get the address this core's DTCM data starts at from SDRAM
    address_t address = data_specification_get_data_address();
    log_info("address is %u\n", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the data spec header");
        return false;
    }

    // initialise my input_buffer for receiving packets
    input_buffer = circular_buffer_initialize(256);
    if (input_buffer == 0){
        return false;
    }
    log_info("input_buffer initialised");

    return true;
}

/****f*
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
    log_info("starting Tensor addition\n");

    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    if(!initialise_recording()){
         rt_error(RTE_SWERR);
    }
    read_input_buffer();
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, MC_PACKET);

    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;


    // Wait till all the binaries are loaded before sending messages.
    // simulation_run() creates a barrier till all binaries are loaded and initialised.
    // So you NEED to use a user interrupt to start things off, because your not using a timer
    simulation_run();
}
