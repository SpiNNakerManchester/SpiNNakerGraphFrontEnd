
//! imports
#include "spin1_api.h"
#include "common-typedefs.h"
#include <data_specification.h>
#include <simulation.h>
#include <debug.h>

//! left shift for each point in the arrived element
#define NORTH              3
#define SOUTH              2
#define EAST               1
#define WEST               0

//! the value expected when each neighbour's data has arrived
#define NORTH_ARRIVED      (1 << NORTH)
#define SOUTH_ARRIVED      (1 << SOUTH)
#define EAST_ARRIVED       (1 << EAST)
#define WEST_ARRIVED       (1 << WEST)
#define NONE_ARRIVED       0

//! the value expected when a combination of neighbours data has arrived
#define NS_ARRIVED         (NORTH_ARRIVED | SOUTH_ARRIVED)
#define EW_ARRIVED         (EAST_ARRIVED | WEST_ARRIVED)
#define ALL_ARRIVED        (NS_ARRIVED | EW_ARRIVED)

//! values for when a certain edge isn't expected
#define NORTH_INIT         (40 << 16)
#define EAST_INIT          (10 << 16)
#define SOUTH_INIT         (10 << 16)
#define WEST_INIT          (40 << 16)

//! how many keys to store before overwriting
#define DEBUG_KEYS         500

//! the visualiser has a bug with negative temperatures!
#define POSITIVE_TEMP      TRUE

//! constants to use in heat diffusion calculation
#define PARAM_CX           0.03125
#define PARAM_CY           0.03125

/*! multicast routing keys to communicate with neighbours */
uint my_key;
uint north_key;
uint south_key;
uint east_key;
uint west_key;

/*! multicast routing keys receivable for injecting temperatures */
uint fake_temp_north_key;
uint fake_temp_south_key;
uint fake_temp_east_key;
uint fake_temp_west_key;

/*! multicast routing keys receivable for commands*/
uint command_pause_key;
uint command_stop_key;
uint command_resume_key;

/*! temperature values */
// any initial value will do!
int my_temp;
int old_temp = 0;

//! get temperatures from 4 neighbours
//! make sure to have room for two values from each neighbour
//! given that the communication is asynchronous
volatile int neighbours_temp[2][4];

/*! coefficients to compute new temperature value */
/*! adjust for 16.16 fixed-point representation  */
int cx_adj = (int) (PARAM_CX * (1 << 16));
int cy_adj = (int) (PARAM_CY * (1 << 16));

/*! keep track of which neighbours have sent data */
/*! cores in the border need special values! */
volatile uint arrived[2];
uint init_arrived;
volatile uint now = 0;
volatile uint next = 1;

//! bool to control if the model should do an update of its element
volatile bool updating = true;

//! control value, which says how many timer ticks to run for before exiting
static uint32_t simulation_ticks = 0;
static uint32_t infinite_run = 0;
static uint32_t time = 0;

//! int as a bool to represent if this simulation should run forever
static uint32_t infinite_run;

//! the unique identifier of this model, so that it can tell if the data its
//! reading is for itself.
#define APPLICATION_MAGIC_NUMBER 0x863e6624

//! human readable definitions of each region in SDRAM
typedef enum regions_e {
    SYSTEM_REGION,
    TRANSMISSIONS,
    NEIGHBOUR_KEYS,
    COMMAND_KEYS,
    TEMP_VALUE,
    RECORDED_DATA,
    BUFFERING_OUT_STATE,
} regions_e;

//! values for the priority for each callback
typedef enum callback_priorities{
    MC_PACKET = -1, SDP = 0, USER = 3, TIMER = 2
} callback_priorities;

//! human readable definitions of each element in the transmission region
typedef enum transmission_region_elements {
    HAS_KEY, MY_KEY
} transmission_region_elements;

//! human readable definitions of each element in the neighbour region
typedef enum neighbour_region_elements {
    EAST_KEY,
    NORTH_KEY,
    WEST_KEY,
    SOUTH_KEY,
    EAST_FAKE_KEY,
    NORTH_FAKE_KEY,
    WEST_FAKE_KEY,
    SOUTH_FAKE_KEY
} neighbour_region_elements;

//! human readable definitions of each element in the command keys region
typedef enum command_region_elements {
    STOP_COMMAND_KEY, PAUSE_COMMAND_KEY, RESUME_COMMAND_KEY
} command_region_elements;

//! human readable definitions of each element in the host output region
typedef enum host_output_region_elements {
    HOST_TRANSMISSION_KEY
} host_output_region_elements;

//! human readable definitions of each element in the initial temperature
//! region
typedef enum initial_temperature_region_elements {
    INITIAL_TEMPERATURE
} initial_temperature_region_elements;

//! if in debug mode, store some tracers
#ifdef DEBUG
uint dbg_packs_receive = 0;
uint * dbg_keys_receive;
uint dbg_timeouts = 0;
uint * dbg_s_time;
#endif


/****f* heat_demo.c/receive_data
 *
 * SUMMARY
 *  This function is used as a callback for packet received events.
 * receives data from 4 (NSEW) neighbours and updates the checklist
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
    sark.vcpu->user1++;
    log_debug("the key i've received is %d\n", key);

#ifdef DEBUG
    dbg_keys_receive[dbg_packs_receive++] = key;
    if (dbg_packs_receive == DEBUG_KEYS) {
        dbg_packs_receive = 0;
    }
#endif

    if (key == north_key) {
        log_debug("received north neighbours temp\n");
        if (arrived[now] & NORTH_ARRIVED) {
            neighbours_temp[next][NORTH] = payload;
            arrived[next] |= NORTH_ARRIVED;
        } else {
            neighbours_temp[now][NORTH] = payload;
            arrived[now] |= NORTH_ARRIVED;
        }
    } else if (key == south_key) {
        log_debug("received south neighbours temp\n");
        if (arrived[now] & SOUTH_ARRIVED) {
            neighbours_temp[next][SOUTH] = payload;
            arrived[next] |= SOUTH_ARRIVED;
        } else {
            neighbours_temp[now][SOUTH] = payload;
            arrived[now] |= SOUTH_ARRIVED;
        }
    } else if (key == east_key) {
        log_debug("received east neighbours temp\n");
        if (arrived[now] & EAST_ARRIVED) {
            neighbours_temp[next][EAST] = payload;
            arrived[next] |= EAST_ARRIVED;
        } else {
            neighbours_temp[now][EAST] = payload;
            arrived[now] |= EAST_ARRIVED;
        }
    } else if (key == west_key) {
        log_debug("received west neighbours temp\n");
        if (arrived[now] & WEST_ARRIVED) {
            neighbours_temp[next][WEST] = payload;
            arrived[next] |= WEST_ARRIVED;
        } else {
            neighbours_temp[now][WEST] = payload;
            arrived[now] |= WEST_ARRIVED;
        }
    } else if (key == fake_temp_north_key) {
        log_debug("received fake north neighbours temp\n");
        neighbours_temp[now][NORTH] = payload;
        neighbours_temp[next][NORTH] = payload;
    } else if (key == fake_temp_east_key) {
        log_debug("received fake east neighbours temp\n");
        neighbours_temp[now][EAST] = payload;
        neighbours_temp[next][EAST] = payload;
    } else if (key == fake_temp_south_key) {
        log_debug("received fake south neighbours temp\n");
        neighbours_temp[now][SOUTH] = payload;
        neighbours_temp[next][SOUTH] = payload;
    } else if (key == fake_temp_west_key) {
        log_debug("received fake west neighbours temp\n");
        neighbours_temp[now][WEST] = payload;
        neighbours_temp[next][WEST] = payload;
    } else if (key == command_stop_key) {
        log_debug("received stop command\n");
        spin1_exit(0);
    } else if (key == command_pause_key) {
        log_debug("received pause command\n");
        updating = false;
    } else if (key == command_resume_key) {
        log_debug("received resume command\n");
        updating = true;
    } else {

        // unexpected packet!
        log_debug("!\n");
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
void send_first_value() {
    log_info("sending out initial temp\n");

    /* send data to neighbours */
    while (!spin1_send_mc_packet(my_key, my_temp, WITH_PAYLOAD)) {
        spin1_delay_us(1);
    }

    log_info("Sent initial temp \n");
}

/****f* heat_demo.c/update
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
        log_info("Simulation complete.\n");

        // falls into the pause resume mode of operating
        simulation_handle_pause_resume(NULL);

        return;
    }

    if (updating) {

        /* report if not all neighbours' data arrived */
#ifdef DEBUG
        if (arrived[now] != ALL_ARRIVED)
        {
            log_debug("@\n");
            dbg_timeouts++;
        }
#endif

        // if a core does not receive temperature from a neighbour
        // it uses it's own as an estimate for the neighbour's.
        if (arrived[now] != ALL_ARRIVED) {
            if (!(arrived[now] & NORTH_ARRIVED)) {
                log_debug("north temp has not arrived by time update "
                          "has occurred\n");
                neighbours_temp[now][NORTH] = my_temp;
            }

            if (!(arrived[now] & SOUTH_ARRIVED)) {
                log_debug("south temp has not arrived by time update "
                          "has occurred\n");
                neighbours_temp[now][SOUTH] = my_temp;
            }

            if (!(arrived[now] & EAST_ARRIVED)) {
                log_debug("east temp has not arrived by time update "
                          "has occurred\n");
                neighbours_temp[now][EAST] = my_temp;
            }

            if (!(arrived[now] & WEST_ARRIVED)) {
                log_debug("west temp has not arrived by time update "
                          "has occurred\n");
                neighbours_temp[now][WEST] = my_temp;
            }
        }

        /* compute new temperature */
        /* adjust for 16.16 fixed-point representation  */
        int tmp1 = neighbours_temp[now][EAST] + neighbours_temp[now][WEST]
                - 2 * my_temp;
        int tmp2 = neighbours_temp[now][NORTH] + neighbours_temp[now][SOUTH]
                - 2 * my_temp;

        /* adjust for 16.16 fixed-point representation  */
        int tmp3 = (int) (((long long) cx_adj * (long long) tmp1) >> 16);
        int tmp4 = (int) (((long long) cy_adj * (long long) tmp2) >> 16);
        my_temp = my_temp + tmp3 + tmp4;

#ifdef POSITIVE_TEMP

        // avoids a problem with negative temperatures in the visualiser!
        my_temp = (my_temp > 0) ? my_temp : 0;
#endif

        log_debug("sending my temp of %d via multicast with key %d\n",
                  my_temp, my_key);
        /* send new data to neighbours */
        while (!spin1_send_mc_packet(my_key, my_temp, WITH_PAYLOAD)) {
            spin1_delay_us(1);
        }
        log_debug("sent my temp via multicast");

        /* prepare for next iteration */
        arrived[now] = init_arrived;
        now = 1 - now;
        next = 1 - next;
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
            &infinite_run, SDP)) {
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
            "this heat element can't effect anything, deduced as an error,"
            "please fix the application fabric and try again\n");
        return false;
    }

    // initialise neighbour keys
    address_t neighbour_region_address = data_specification_get_region(
        NEIGHBOUR_KEYS, address);

    // get east key
    east_key = neighbour_region_address[EAST_KEY];
    log_info("my east neighbours key is %d\n", east_key);
    if (east_key == 0xFFFFFFFF) {
        neighbours_temp[now][NORTH] = EAST_INIT;
        neighbours_temp[next][NORTH] = EAST_INIT;
        init_arrived |= EAST_ARRIVED;
    }

    // get north key
    north_key = neighbour_region_address[NORTH_KEY];
    log_info("my north neighbours key is %d\n", north_key);
    if (north_key == 0xFFFFFFFF) {
        neighbours_temp[now][NORTH] = NORTH_INIT;
        neighbours_temp[next][NORTH] = NORTH_INIT;
        init_arrived |= NORTH_ARRIVED;
    }

    // get west key
    west_key = neighbour_region_address[WEST_KEY];
    log_info("my west neighbours key is %d\n", west_key);
    if (west_key == 0xFFFFFFFF) {
        neighbours_temp[now][WEST] = WEST_INIT;
        neighbours_temp[next][WEST] = WEST_INIT;
        init_arrived |= WEST_ARRIVED;
    }

    // get south key
    south_key = neighbour_region_address[SOUTH_KEY];
    log_info("my south neighbours key is %d\n", south_key);
    if (south_key == 0xFFFFFFFF) {
        neighbours_temp[now][SOUTH] = SOUTH_INIT;
        neighbours_temp[next][SOUTH] = SOUTH_INIT;
        init_arrived |= SOUTH_ARRIVED;
    }

    // prepare for first update
    arrived[now] = init_arrived;
    arrived[next] = init_arrived;

    // locate fake injected temp keys
    fake_temp_east_key = neighbour_region_address[EAST_FAKE_KEY];
    log_info("my fake east temp key is %d\n", fake_temp_east_key);
    fake_temp_north_key = neighbour_region_address[NORTH_FAKE_KEY];
    log_info("my fake north temp key is %d\n", fake_temp_north_key);
    fake_temp_west_key = neighbour_region_address[WEST_FAKE_KEY];
    log_info("my fake west temp key is %d\n", fake_temp_west_key);
    fake_temp_south_key = neighbour_region_address[SOUTH_FAKE_KEY];
    log_info("my fake south temp key is %d\n", fake_temp_south_key);

    // initialise command keys
    address_t command_region_address = data_specification_get_region(
            COMMAND_KEYS, address);
    command_stop_key = command_region_address[STOP_COMMAND_KEY];
    log_info("my stop command is %d\n", command_stop_key);
    command_pause_key = command_region_address[PAUSE_COMMAND_KEY];
    log_info("my pause command is %d\n", command_pause_key);
    command_resume_key = command_region_address[RESUME_COMMAND_KEY];
    log_info("my resume command is %d\n", command_resume_key);

    // report if command keys are special values
    if (command_pause_key == 0 && command_stop_key == 0
            && command_resume_key == 0){
        log_info("Currently running without commands set\n");
    }

    // read my temperature
    address_t my_temp_region_address = data_specification_get_region(
        TEMP_VALUE, address);
    my_temp = my_temp_region_address[INITIAL_TEMPERATURE];
    log_info("my initial temp is %d\n", my_temp);
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
void c_main() {
    log_info("starting heat_demo\n");

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
    spin1_callback_on(MC_PACKET_RECEIVED, receive_data_void, MC_PACKET);
    spin1_callback_on(TIMER_TICK, update, TIMER);

#ifdef DEBUG

    // initialise variables
    dbg_keys_receive = spin1_malloc(DEBUG_KEYS * 4 * sizeof(uint));

    // record start time somewhere in SDRAM
    dbg_s_time = (uint *) (SPINN_SDRAM_BASE + 4 * spin1_get_core_id());
    *dbg_s_time = sv->clock_ms;
#endif

    // start execution
    log_info("Starting\n");

    // Start the time at "-1" so that the first tick will be 0
    time = UINT32_MAX;

    simulation_run();
}
