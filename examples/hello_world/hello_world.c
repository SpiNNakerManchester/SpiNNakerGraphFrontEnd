/****a* hello_world.c/hello_world_summary
*
* COPYRIGHT
*  Copyright (c) The University of Manchester, 2011. All rights reserved.
*  SpiNNaker Project
*  Advanced Processor Technologies Group
*  School of Computer Science
*  Author: Arthur Ceccotti
*******/

#include "spin1_api.h"
#include "common-typedefs.h"
#include "recording.h"
#include <data_specification.h>
#include <debug.h>

typedef enum regions_e {
    SYSTEM_REGION, STRING_DATA_REGION
} regions_e;

void record_data() {
    log_info("Recording data...");

    uint chip = spin1_get_chip_id();

    // TODO little hack which only works on 4 chip boards...
    char* chip_chars;
    if(chip == 0)       { chip_chars = "0, 0";}
    else if(chip == 1)  { chip_chars = "0, 1";}
    else if(chip == 256){ chip_chars = "1, 0";}
    else if(chip == 257){ chip_chars = "1, 1";}
    else                { chip_chars = "?, ?";}

    uint core = spin1_get_core_id();

    log_info("Issuing 'Hello World' from chip %d (%s), core %d", chip, chip_chars, core);

    // TODO quick and DIRTY hack to convert a 2 digit int into a string. Using sprintf breaks the DTCM...
    char core_chars[2] = { core > 9 ? (core/10) + '0' : ' ', core > 9 ? (core%10) + '0' : core + '0' };

    char hello_me[50];
    hello_me[0] = '\0';
    strcat(hello_me, "Hello World from ");
    strcat(hello_me, chip_chars);
    strcat(hello_me, ", ");
    strcat(hello_me, core_chars);

    bool recorded = recording_record(e_recording_channel_spike_history,
                                     hello_me, strlen(hello_me));

    if(recorded){ log_info("Hello World recorded successfully!"); }
    else        { log_error("Hello World was not recorded...");   }
}

void iobuf_data(){
    address_t address = data_specification_get_data_address();

    address_t hello_world_address = data_specification_get_region(STRING_DATA_REGION, address);

    log_info("Hello world address is %08x", hello_world_address);

    char* my_string = &hello_world_address[1];
    log_info("Data read is: %s", my_string);
}

static bool initialize() {

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();
    
    log_info("DataSpec data address is %08x", address);

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("Could not read DataSpec header");
        return false;
    }

    address_t system_region = data_specification_get_region(SYSTEM_REGION, address);
    address_t data_region   = data_specification_get_region(STRING_DATA_REGION, address);

    log_info("System region: %08x", system_region);
    log_info("Data region: %08x", data_region);

    uint32_t data_region_size = 500;

                                               // TODO should make my own channel
    if (!recording_initialse_channel(data_region, e_recording_channel_spike_history, data_region_size)) {
        log_error("Could not initialize channel.");
        return false;
    }

    log_info("Initialization completed successfully!");
    return true;
}

void update (uint ticks, uint b)
{
    // I give it a few ticks between reading and writing, just in case
    // the IO operations take a bit of time
    if(ticks == 1)          { record_data(); }
    else if(ticks == 100)   { iobuf_data();  }
    else if(ticks == 200)   { recording_finalise();
                              spin1_exit(0);}
}

void c_main()
{
    log_info("Initializing Distributed Hello World...");

    if (!initialize()) {
        rt_error(RTE_SWERR);
    }

    // set timer tick value to 100ms
    spin1_set_timer_tick(100);

    // register callbacks
    spin1_callback_on (TIMER_TICK, update, 0);

    simulation_run();
}