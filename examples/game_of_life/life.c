/*
  life.c - written by Steve Furber and Alan Stokes - April 2015

  This example program demonstrates the use of Tubogrid to get simple
  per-core animation. It implements Conway's Life .
*/


//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

/*! multicast routing keys to communicate with neighbours */
uint my_key;
/*! setter for if i should record data to sdram*/
uint should_record_to_sdram;

//! this cell's state
uint alive;
//! the number of alive neigubours needed to keep this cell alive.
uint theshold;
//! previous state
uint last_alive;
//! live neighbour count [for each gen]
uint count;
//! generation (used for parity)
uint gen;
//! control vlaue, which says how many timer tics to run for before exiting
static uint32_t simulation_ticks;
//! the unqieu identifier of this model, so that it can tell if the data its
//! reading is for itself.
#define APPLICATION_MAGIC_NUMBER 0xABCE

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION, TRANSMISSIONS, STATE_REGION, RECORDING_REGION,
} regions_e;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
}transmission_region_elements;

//! human readable definitions of each element in the initial state region
typedef enum initial_state_region_elements {
    INITIAL_STATE, THESHOLD,
}initial_state_region_elements;

//! human readable definitions of each element in the recoridng region config
typedef enum recording_region_config_elements {
    SET_TO_RECORD
}recording_region_config_elements;

/****f* life.c/report_state
*
* SUMMARY
*  This function is used to report current temp
*
* SYNOPSIS
*  void report_state (uint ticks)
*
* SOURCE
*/
void report_state(uint ticks)
{
    // if the model is set to record, then locate the right address to
    //write current temp into
    if (should_record_to_sdram){
         // Copy data into recording channel
         address_t address = data_specification_get_data_address();
         address_t my_recording_region_address = data_specification_get_region(
              RECORDING_REGION, address);
         // 2 is for "does record and initial value)
         address_t place_to_record = my_recording_region_address + 1 + ticks;
         log_debug("recording_region_address is %d", my_recording_region_address);
         spin1_memcpy(place_to_record, &alive, 1);
         log_debug("recorded state %d for tick %d at address %d",
                   alive, ticks, place_to_record);
    }
}

/****f* life.c/receive_data
*
* SUMMARY
*  This function is used as a callback for packet received events.
* receives data from neighbours and updates the checklist
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
void receive_data(uint key, uint payload)
{
    log_debug("the key ive recieved is %d with payload %d \n", key, payload);
    // count[gen mod 2] += alive
    if (payload == 1){
        count +=1;
    }
}

/****f* heat_demo.c/send_first_value
*
* SUMMARY
*
* SYNOPSIS
*  void send_first_value (uint a, uint b)
*
* SOURCE
*/
void send_first_value(uint a, uint b)
{
    use(a);
    use(b);
    log_debug("sending out inital state\n");
    /* send data to neighbours */
    while(! spin1_send_mc_packet(my_key, alive, WITH_PAYLOAD)){
        spin1_delay_us(1);
    }
}


/****f* life.c/update
*
* SUMMARY
*
* SYNOPSIS
*  void update (uint ticks, uint b)
*
* SOURCE
*/
void update(uint ticks, uint b)
{
    use(b);

    log_debug("on tick %d", ticks);
    log_debug("have recieved %d alive packets", count);
    // check that the run time hasnt already alapsed and thus needs to be killed
    if (ticks == simulation_ticks){
        log_info("Simulation complete.\n");
        spin1_exit(0);
        return;
    }

    // traditional conways game of life rules:
    // http://en.wikipedia.org/wiki/Conway%27s_Game_of_Life
    // http://www.bitstorm.org/gameoflife/
    // http://www.conwaylife.com/wiki/Conway%27s_Game_of_Life
    // and many many more.
    if (alive == 1){
        if(count < 2){
             alive = 0;
        }
        else if(count == 2 && count == 3){
            alive = 1;
        }
        else if(count > 3){
            alive = 0;
        }
    }
    else{
        if(count == 3){
            alive = 1;
        }
        else{
            alive = 0;
        }
    }


    //alive = (count[gen] | alive) == theshold;		// Life automaton rule
    count = 0;						            // clear count for next gen

    // send state to neighbours
    spin1_send_mc_packet (my_key, alive, WITH_PAYLOAD);

    if (alive != last_alive){
        last_alive = alive;
    }

    if(should_record_to_sdram){
        report_state(ticks);
    }
}

//! \brief this method is to catch strange behaviour
//! \param[in] key: the key being recieved
//! \param[in] uknown: second arg with no state. set to zero by deault
void receive_data_void(uint key, uint unknown){
    use(key);
    use(unknown);
    log_error("this should never ever be done\n");
}

static bool initialize(uint32_t *timer_period) {
    log_info("Initialise: started\n");

    // Get the address this core's DTCM data starts at from SRAM
    address_t address = data_specification_get_data_address();

    // Read the header
    if (!data_specification_read_header(address)) {
        log_error("failed to read the dataspec header");
        return false;
    }

    // Get the timing details
    address_t system_region = data_specification_get_region(
        SYSTEM_REGION, address);
    if (!simulation_read_timing_details(
            system_region, APPLICATION_MAGIC_NUMBER, &timer_period,
            &simulation_ticks)) {
        log_error("failed to read the system header");
        return false;
    }

    // output message about length of time to run
    log_debug("i plan to run for %d timer ticks", simulation_ticks);

    // initlise transmission keys
    address_t transmission_region_address =  data_specification_get_region(
        TRANSMISSIONS, address);
    if (transmission_region_address[HAS_KEY] == 1){
        my_key = transmission_region_address[MY_KEY];
        log_debug("my key is %d\n", my_key);
    }
    else {
        log_error("this heat element cant effect anything, deduced as an error,"
                  "please fix the application fabric and try again\n");
        return false;
    }

    // read my initial state
    address_t state_region_address =  data_specification_get_region(
        STATE_REGION, address);
    alive = state_region_address[INITIAL_STATE];
    last_alive = alive;
    theshold = state_region_address[THESHOLD];
    log_debug("my initial state is %d", alive);
    log_debug("my theshold is %d", theshold);

    // read if im recording
    address_t my_recording_region_address = data_specification_get_region(
        RECORDING_REGION, address);
    should_record_to_sdram = my_recording_region_address[SET_TO_RECORD];
    log_debug("if i should record is set to %d\n", should_record_to_sdram);
    return true;
}


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
void c_main()
{
    log_info("starting game of life cell\n");
    // Load DTCM data
    uint32_t timer_period;

    // initialise the model
    if (!initialize(&timer_period)){
    	rt_error(RTE_API);
    }

    // set timer tick value to 1ms (in microseconds)
    // slow down simulation to alow users to appreciate changes
    log_debug("setting timer to execute every %d microseconds", timer_period);
    spin1_set_timer_tick(timer_period);

    // register callbacks
    spin1_callback_on(MCPL_PACKET_RECEIVED, receive_data, 0);
    spin1_callback_on(MC_PACKET_RECEIVED, receive_data_void, 0);
    spin1_callback_on(TIMER_TICK, update, -1);

    // kick-start the update process
    spin1_schedule_callback(send_first_value, 0, 0, 3);

    // start execution
    log_info("Starting\n");
    simulation_run();
    log_debug("ending game of life cell");
}