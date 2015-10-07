/****a* heat_demo.c/heat_demo_summary
*
* COPYRIGHT
*  Copyright (c) The University of Manchester, 2011. All rights reserved.
*  SpiNNaker Project
*  Advanced Processor Technologies Group
*  School of Computer Science
*
*******/

//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include "recording.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>


/****f* heat_demo.c/update
*
* SUMMARY
*
* SYNOPSIS
*  void update (uint ticks, uint b)
*
* SOURCE
*/


#define N_RECORDING_CHANNELS 1

typedef enum regions_e {
    SYSTEM_REGION, SPIKE_HISTORY
} regions_e;


/*
static bool initialize() {
    log_info("Initialise: started");

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    io_printf (IO_BUF, "Address is %x \n", address);

    // Read the header
  //  if (!data_specification_read_header(address)) {
  //      return false;
   // }

    // Set up recording
    recording_channel_e channels_to_record[] = {
        e_recording_channel_spike_history
    };

    regions_e regions_to_record[] = {
        STRING_RECORDING_REGION
    };

    uint32_t region_sizes[N_RECORDING_CHANNELS];

    for (uint32_t i = 0; i < N_RECORDING_CHANNELS; i++) {
        if (recording_is_channel_enabled(recording_flags,
                                         channels_to_record[i])) {
            if (!recording_initialse_channel(
                    data_specification_get_region(regions_to_record[i],
                                                  address),
                    channels_to_record[i], region_sizes[i])) {
                log_info("Returning false on the initialise!!");
                return false;
            }
        }
    }

    log_info("Initialise: finished");
    return true;
}*/


/****f* heat_demo.c/c_main
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

/*
uint32_t my_int;


static bool initialize() {
    log_info("Initializing.........");

    my_int = (uint32_t) sark_alloc(sizeof(uint32_t), 1);

    if (my_int == NULL) {
        log_error("Could not allocate uint32_t :(");
        return false;
    }
    //out_spikes_reset();
    return true;
}
*/



////////////////////////////////////////
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run;
static uint32_t recording_flags = 0;


char a = 'A';

void record_me() {
    log_info("RECORD ME BEING CALLED");
    if (recording_is_channel_enabled(
            recording_flags, e_recording_channel_spike_history)) {
        bool recorded = recording_record(
            e_recording_channel_spike_history, a, sizeof(char));

        log_info("WAS recorded: %d", recorded);
    }
    else{
        log_info("Recording channel was NOT ENABLED!");
    }
}


//
//void record_me() {
//    log_info("RECORD ME BEING CALLED");
//    if (recording_is_channel_enabled(
//            recording_flags, e_recording_channel_spike_history)) {
//        recording_record(
//            e_recording_channel_spike_history, 12345, sizeof(uint32_t));
//    }
//}

void read_me(){
    address_t address = data_specification_get_data_address();

    address_t my_temp_region_address =  data_specification_get_region(
       SPIKE_HISTORY, address);

    uint32_t my_temp = my_temp_region_address[0];
    log_info("READING NOW %d", my_temp);
}

static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started");

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        log_info("Data spec not working.....");
        return false;
    }

    log_info("Name hash is %08x", APPLICATION_NAME_HASH);

    // Get the timing details
    address_t system_region = data_specification_get_region(SYSTEM_REGION, address);

    log_info("Got system region: %08x", system_region);

    address_t spike_history_addr = data_specification_get_region(SPIKE_HISTORY, address);

    log_info("Got SPIKE HISTORY region: %08x", spike_history_addr);

    // Get the recording information
    uint32_t spike_history_region_size;
    recording_read_region_sizes(
        &system_region[SIMULATION_N_TIMING_DETAIL_WORDS],
        &recording_flags, &spike_history_region_size, NULL, NULL);

    if (recording_is_channel_enabled(recording_flags, e_recording_channel_spike_history)) {
        if (!recording_initialse_channel(spike_history_addr,
                e_recording_channel_spike_history, spike_history_region_size)) {
            log_info("Returning FALSE because recording_initialse_channel failed.");
            return false;
        }
        else{
            log_info("Recording channel should now be OK!");
        }
    }
    else{
        log_info("channel isn't even enabled BRO");
    }

    log_info("Initialise: completed successfully!!!!!!1");

    return true;
}

//////////////////////////////////


void update (uint ticks, uint b)
{
    //log_info("HELLO WORLD from chip {}, core {}".format(chip, core));

    if(ticks == 100){
        uint chip = spin1_get_chip_id ();				// get chip ID
        uint core = spin1_get_core_id ();				// ...& core ID

        log_info ("hello world from chip %d, core %d\n", chip, core);

        record_me();
    }

    if(ticks == 200){
        read_me();
    }


    if(ticks == 300){
        recording_finalise();
        spin1_exit(0);
    }

}

void c_main()
{
    // Load DTCM data
    uint32_t timer_period;
    if (!initialize(&timer_period)) {
        rt_error(RTE_SWERR);
    }

    timer_period = 100;

    // set timer tick value to 1ms (in microseconds)
    // slow down simulation to allow users to appreciate changes
    spin1_set_timer_tick(timer_period);

    // register callbacks
    //spin1_callback_on (MCPL_PACKET_RECEIVED, receive_data, 0);
    //spin1_callback_on (MC_PACKET_RECEIVED, receive_data_void, 0);
    spin1_callback_on (TIMER_TICK, update, 0);

    //spin1_start (SYNC_NOWAIT);					// start event-driven operation

    simulation_run();
}